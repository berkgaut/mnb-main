from pathlib import PurePosixPath
from typing import Union, Optional, Tuple, Iterable


class PlanBuilderException(Exception):
    pass


InputT = Union['InputFile', 'Stdin']
OutputT = Union['OutputFile', 'OutputStream']


class Plan:
    """
    Class with builder-style API to represent execution plan
    """
    required_api: Tuple[Optional[int], Optional[int]] = (None, None)
    _images: dict[str, 'Image'] = dict()
    _files: dict[PurePosixPath, 'WorkFile'] = dict()
    _execs: list['Exec'] = list()

    def require_api(self, major: int, minor: Optional[int]) -> 'Plan':
        """Specify minimum API version required by plan"""
        self.required_api = (major, minor)
        return self

    def image(self, name: str) -> 'Image':
        if name in self._images:
            return self._images[name]
        else:
            new_image = Image(name)
            self._images[name] = new_image
            return new_image

    def file(self, posix_path: Union[str, PurePosixPath], secret: bool = False) -> 'WorkFile':
        path = PurePosixPath(posix_path)
        key = (path, secret)
        if key in self._files:
            return self._files[key]
        else:
            new_workfile = WorkFile(self, path, secret)
            self._files[key] = new_workfile
            return new_workfile

    def exec(self,
             image: Union['Image'],
             command: list[Union[str, 'CommandElement']],
             inputs: Optional[list[InputT]] = None,
             outputs: Optional[list[OutputT]] = None,
             entrypoint: Optional[str] = None) -> 'Exec':
        new_exec_builder = Exec(self, image, command, inputs, outputs, entrypoint)
        self._execs.append(new_exec_builder)
        return new_exec_builder

    def images(self) -> Iterable['Image']:
        return self._images.values()

    def files(self) -> Iterable['WorkFile']:
        return self._files.values()

    def execs(self) -> Iterable['Exec']:
        return self._execs


class Exec:
    image: 'Image'
    command: list[str]
    inputs: list[InputT]
    outputs: list[OutputT]
    entrypoint: Optional[str]

    def __init__(self, plan, image, command, inputs, outputs, entrypoint):
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
                    self.inputs.append(cmdel)

    def input(self, input: InputT) -> 'Exec':
        self.inputs.append(input)
        return self

    def output(self, output: OutputT) -> 'Exec':
        self.outputs.append(output)
        return self


class WorkFile:
    posix_path: PurePosixPath
    #plan: Plan
    secret: bool

    def __init__(self, plan, path: Union[str, PurePosixPath], secret: bool):
        #self.plan = plan
        self.posix_path = PurePosixPath(path)
        self.secret = secret

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


class InputFileThroughEnv:
    workfile: WorkFile
    name: str

    def __init__(self, workfile, name):
        self.workfile = workfile
        self.name = name


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


class Stdin:
    workfile: WorkFile

    def __init__(self, workfile):
        self.workfile = workfile

    def as_command_element(self) -> str:
        return "-"

    def is_input(self) -> bool:
        return True


class OutputStream:
    workfile: WorkFile
    through_stdout: bool = False
    through_stderr: bool = False

    # there would be also joined stdout and stdin opyion

    def __init__(self, workfile, stdout=False, stderr=False):
        self.workfile = workfile
        self.through_stdout, self.stderr = stdout, stderr


class Image:
    name: str
    build_from_context: Optional[PurePosixPath] = None
    pull_from_registry: bool = False

    def __init__(self, name: str):
        self.name = name

    def from_context(self, path: Union[str, PurePosixPath]):
        self._ensure_not_initialized()
        self.build_from_context = PurePosixPath(path)
        return self

    def from_registry(self):
        self._ensure_not_initialized()
        self.pull_from_registry = True
        return self

    def _ensure_not_initialized(self):
        if self.build_from_context or self.pull_from_registry:
            if self.build_from_context:
                msg = "build from %s" % self.build_from_context
            else:
                msg = "pull from registry"
            raise PlanBuilderException("image %s already specified as %s", (self.name, msg))
