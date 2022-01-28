import itertools
from pathlib import PurePosixPath
from typing import Union, Optional, Tuple, Iterable

class PlanBuilderException(Exception):
    pass

class PlanParsinExceotion(Exception):
    pass

InputT = Union['InputFile', 'Stdin', 'InputFileThroughEnv']
OutputT = Union['OutputFile', 'OutputStream']

class Plan:
    """
    Class with builder-style API to represent execution plan
    """
    _required_api: Tuple[Optional[int], Optional[int]]
    _images: dict[str, 'Image']
    _files: dict[(PurePosixPath, bool), 'WorkFile']
    _execs: list['Exec']

    def __init__(self):
        self._required_api = (None, None)
        self._images = dict()
        self._files = dict()
        self._execs = list()

    def require_api(self, major: int, minor: Optional[int] = None) -> 'Plan':
        """Specify minimum API version required by plan"""
        self._required_api = (major, minor)
        return self

    def image(self, name: str) -> 'Image':
        """
        reference to an image
        """
        return self._images[name]

    def pull_image(self, name: str) -> 'Image':
        """
        Declare image <name> as pulled from a registry
        """
        return self._add_image(name, Image(name, pull_from_registry=True))

    def build_image(self, name: str, context_path: [str, PurePosixPath]) -> 'Image':
        """
        Declare image <name> as built from a context <context_path>
        """
        return self._add_image(name, Image(name, build_from_context=PurePosixPath(context_path)))

    def _add_image(self, name: str, new_image: 'Image') -> 'Image':
        if name in self._images:
            original_image = self._images[name]
            if original_image != new_image:
                raise PlanBuilderException(
                    "Image redefinition conflict, original=%s, new=%s" % (original_image, new_image))
            else:
                return original_image
        else:
            self._images[name] = new_image
            return new_image

    def file(self, posix_path: Union[str, PurePosixPath], secret: bool = False) -> 'WorkFile':
        path = PurePosixPath(posix_path)
        key = (path, secret)
        if key in self._files:
            return self._files[key]
        else:
            new_workfile = WorkFile(path, secret)
            self._files[key] = new_workfile
            return new_workfile

    def exec(self,
             image: 'Image',
             command: list[Union[str, 'CommandElement']],
             inputs: Optional[list[InputT]] = None,
             outputs: Optional[list[OutputT]] = None,
             entrypoint: Optional[str] = None) -> 'Exec':
        new_exec = Exec(image, command, inputs, outputs, entrypoint)
        self._execs.append(new_exec)
        return new_exec

    def images(self) -> Iterable['Image']:
        return self._images.values()

    def files(self) -> Iterable['WorkFile']:
        return self._files.values()

    def execs(self) -> Iterable['Exec']:
        return self._execs

    def to_json(self):
        return dict(
            mnb_required_api=dict(major=self._required_api[0],
                                  minor=self._required_api[1]),
            plan=[x.to_json() for x in itertools.chain(self.images(), self.files(), self.execs())])

    @classmethod
    def from_json(cls, data) -> 'Plan':
        plan = Plan()
        parser = PlanParser(plan)
        parser.process(data)
        return plan

class PlanParser:
    def __init__(self, plan):
        self.plan = plan

    def process(self, data):
        mnb_required_api = data.get('mnb_required_api')
        if mnb_required_api:
            major = mnb_required_api.get('major')
            minor = mnb_required_api.get('minor')
            self.plan.require_api(major, minor)
        plan_elements = data.get('plan', [])
        for plan_element in plan_elements:
            self.plan_element_from_json(plan_element)

    def plan_element_from_json(self, plan_element):
        if not isinstance(plan_element, dict) or len(plan_element) != 1:
            raise Exception("invalid plan element: %s" % plan_element)
        [(tag, data)] = plan_element.items()
        if tag == "image":
            self.process_image(plan_element)
        elif tag == "file":
            self.process_file(plan_element)
        elif tag == "exec":
            self.process_exec(plan_element)
        else:
            raise Exception("invalid plan element: ")

    def process_image(self, plan_element):
        image = plan_element.get('image')
        if image.get('build') is not None:
            build = image.get('build')
            self.plan.build_image(image.get("name"), build.get("context_path"))
        elif image.get("pull") is not None:
            pull = image.get("pull")
            return self.plan.pull_image(image.get("name"))
        else:
            raise Exception("invalid image: %s", plan_element)

    def process_file(self, plan_element):
        file = plan_element.get("file")
        self.plan.file(file.get("path"), file.get("secret"))

    def process_exec(self, plan_element):
        exec = plan_element.get("exec")
        return self.plan.exec(
            image=self.plan.image(exec.get("image")),
                command=exec.get("command"),
                inputs=[self.input_from_json(x) for x in exec.get("inputs", [])],
                outputs=[self.output_from_json(x) for x in exec.get("outputs", [])],
                entrypoint=exec.get("entrypoint"))

    def input_from_json(self, data):
        value = self.value_from_json(data.get("value"))
        through = data.get("through")
        if through.get("input_file") is not None:
            input_file = through.get("input_file")
            return value.as_input(through_path=input_file.get("path"))
        elif through.get("stdin") is not None:
            return value.through_stdin()
        elif through.get("environment_variable"):
            environment_variable = through.get("environment_variable")
            return value.through_env(environment_variable.get("name"))
        else:
            raise Exception("invalid input: %s" % data)

    def output_from_json(self, data):
        value = self.value_from_json(data.get("value"))
        through = data.get("through")
        if through.get("output_file") is not None:
            output_file = through.get("output_file")
            return value.as_output(through_path=output_file.get("path"))
        elif through.get("stdout") is not None:
            return value.through_stdout()
        elif through.get("stderr") is not None:
            return value.through_stderr()
        else:
            raise Exception("invalid output: %s" % data)

    def value_from_json(self, data):
        if data.get("file"):
            file = data.get("file")
            return self.plan.file(file.get("path"), file.get("secret"))
        else:
            raise Exception("invalid value: %s" % data)

class Exec:
    image: 'Image'
    command: list[str]
    inputs: list[InputT]
    outputs: list[OutputT]
    entrypoint: Optional[str]

    def __init__(self, image, command, inputs, outputs, entrypoint):
        if inputs is None:
            inputs = list()
        if outputs is None:
            outputs = list()
        self.image = image
        self.inputs = inputs
        self.outputs = outputs
        self.entrypoint = entrypoint
        self.command = list()
        for cmdel in command:
            if isinstance(cmdel, str):
                self.command.append(cmdel)
            elif isinstance(cmdel, CommandElement):
                self.command.append(cmdel.as_command_element())
                if cmdel.is_input():
                    self.inputs.append(cmdel)
                if cmdel.is_output():
                    self.outputs.append(cmdel)

    def __str__(self):
        return "exec(%s)" % self.image

    def input(self, input: InputT) -> 'Exec':
        self.inputs.append(input)
        return self

    def output(self, output: OutputT) -> 'Exec':
        self.outputs.append(output)
        return self

    def to_json(self):
        return dict(exec=dict(
            image=self.image.name,
            command=self.command,
            entrypoint=self.entrypoint,
            inputs=[x.to_json() for x in self.inputs],
            outputs=[x.to_json() for x in self.outputs]))


class WorkFile:
    posix_path: PurePosixPath
    secret: bool

    def __init__(self, path: Union[str, PurePosixPath], secret: bool):
        self.posix_path = PurePosixPath(path)
        self.secret = secret

    def __str__(self):
        return repr(str(self.posix_path))

    def path(self) -> PurePosixPath:
        return self.posix_path

    def replace_suffix(self, old_suffix, new_suffix):
        raise NotImplementedError("as of yet")

    def as_input(self, through_path: Optional[Union[str, PurePosixPath]] = None) -> 'InputFile':
        return InputFile(self, through_path)

    def through_stdin(self) -> 'Stdin':
        return Stdin(self)

    def through_env(self, name: str) -> 'InputFileThroughEnv':
        return InputFileThroughEnv(self, name)

    def as_output(self, through_path=None) -> 'OutputFile':
        if self.secret:
            raise PlanBuilderException("secrets could not be outputs")
        return OutputFile(self, through_path)

    def through_stdout(self) -> 'OutputStream':
        if self.secret:
            raise PlanBuilderException("secrets could not be outputs")
        return OutputStream(self, stdout=True)

    def through_stderr(self) -> 'OutputStream':
        if self.secret:
            raise PlanBuilderException("secrets could not be outputs")
        return OutputStream(self, stderr=True)

    def to_json(self):
        return dict(file=dict(path=str(self.posix_path), secret=self.secret))


class CommandElement:
    def as_command_element(self) -> str:
        raise NotImplementedError

    def is_input(self) -> bool:
        raise NotImplementedError

    def is_output(self) -> bool:
        return not self.is_input()


class InputFile(CommandElement):
    workfile: WorkFile
    through_path: PurePosixPath

    def __init__(self, workfile: WorkFile, through_path: Optional[Union[str, PurePosixPath]]):
        self.workfile = workfile
        if through_path:
            self.through_path = PurePosixPath(through_path)
        else:
            self.through_path = workfile.path()

    def as_command_element(self) -> str:
        return str(self.through_path)

    def is_input(self) -> bool:
        return True

    def to_json(self):
        return dict(through=self._to_json1(), value=self.workfile.to_json())

    def _to_json1(self):
        return dict(input_file=dict(path=str(self.through_path)))


class InputFileThroughEnv:
    workfile: WorkFile
    name: str

    def __init__(self, workfile, name):
        self.workfile = workfile
        self.name = name

    def to_json(self):
        return dict(through=self._to_json1(), value=self.workfile.to_json())

    def _to_json1(self):
        return dict(environment_variable=dict(name=self.name))


class OutputFile(CommandElement):
    workfile: WorkFile
    through_path: PurePosixPath

    def __init__(self, workfile, through_path: Optional[Union[str, PurePosixPath]]):
        self.workfile = workfile
        if through_path:
            self.through_path = PurePosixPath(through_path)
        else:
            self.through_path = workfile.path()

    def as_command_element(self) -> str:
        if self.through_path:
            return str(self.through_path)
        else:
            return str(self.workfile.path())

    def is_input(self) -> bool:
        return False

    def to_json(self):
        return dict(through=self._to_json1(), value=self.workfile.to_json())

    def _to_json1(self):
        return dict(output_file=dict(path=str(self.through_path)))


class Stdin:
    workfile: WorkFile

    def __init__(self, workfile):
        self.workfile = workfile

    def as_command_element(self) -> str:
        return "-"

    def is_input(self) -> bool:
        return True

    def to_json(self):
        return dict(through=self._to_json1(), value=self.workfile.to_json())

    def _to_json1(self):
        return dict(stdin=dict())

class OutputStream:
    workfile: WorkFile
    through_stdout: bool = False
    through_stderr: bool = False

    # there would be also joined stdout and stdin option

    def __init__(self, workfile, stdout=False, stderr=False):
        self.workfile = workfile
        self.through_stdout, self.through_stderr = stdout, stderr

    def to_json(self):
        return dict(through=self._to_json1(), value=self.workfile.to_json())

    def _to_json1(self):
        if self.through_stdout:
            return dict(stdout=dict())
        elif self.through_stderr:
            return dict(stderr=dict())


class Image:
    name: str
    build_from_context: Optional[PurePosixPath]
    pull_from_registry: bool

    def __init__(self, name: str, pull_from_registry: bool = False, build_from_context: Optional[PurePosixPath] = None):
        if pull_from_registry and build_from_context:
            raise PlanBuilderException(
                "Ambiguous definition (image could be either pulled from registry or built, but not both), image name=%s" % name)
        if not pull_from_registry and (build_from_context is None):
            raise PlanBuilderException(
                "Incomplete definition (image should be either pulled from registry or built), image name=%s" % name)
        self.name = name
        self.pull_from_registry = pull_from_registry
        self.build_from_context = build_from_context

    def __str__(self):
        return self.name

    # Hash & equality defined to allow Plan check for conflicting image declarations
    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Image):
            return False
        else:
            return self.name == o.name and self.build_from_context == o.build_from_context and self.pull_from_registry == o.pull_from_registry

    def __hash__(self) -> int:
        return hash((self.name, self.build_from_context, self.pull_from_registry))

    def to_json(self):
        spec = dict(name=self.name, pull=dict()) if self.pull_from_registry \
            else dict(name=self.name, build=dict(context_path=str(self.build_from_context)))
        return dict(image=spec)
