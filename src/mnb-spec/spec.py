from pathlib import PurePosixPath
from typing import Union, Optional, Tuple, Dict, List
import json
import sys

ImageName = str
ImageSpec = Union[ImageName, 'PullImage', 'BuildImage']
Action = Union['PullImage', 'BuildImage', 'Exec']
Value = Union['File', 'Dir', 'Image']
InputThrough = Union['ThroughFile', 'ThroughDir', 'ThroughEnvironment', 'ThroughStdin']
OutputThrough = Union['ThroughFile', 'ThroughDir', 'ThroughStdout', 'ThroughStderr']
CommandElement = Union[str, 'File', 'Dir', PurePosixPath]

StringOrPath = Union[str, PurePosixPath]

class Spec:
    spec_version: Tuple[int, int]
    actions: List['Action']
    description: Optional[str]

    def __init__(self, spec_version: Tuple[int, int], actions: Optional[List['Action']] = None, description: Optional[str] = None):
        self.spec_version = spec_version
        self.description = description
        if actions is None:
            self.actions = list()
        else:
            self.actions = actions

    #### ContextManager interface to dump JSON in the end ####
    def __enter__(self):
        return self

    def __exit__(self, *ignored):
        print_spec_json(self)

    #### Helpers ####
    def pull_image(self, image_spec: ImageSpec) -> 'PullImage':
        action = PullImage(get_image_name(image_spec))
        self.actions.append(action)
        return action

    def build_image(self,
                    image_spec: ImageSpec,
                    extra_tags: Optional[List[str]] = None,
                    context_path: Optional[StringOrPath] = None,
                    build_args: Optional[dict[str, str]] = None,
                    dockerfile_path: Optional[StringOrPath] = None,
                    from_git: Optional['FromGit'] = None) -> 'BuildImage':
        action = BuildImage(get_image_name(image_spec),
                            extra_tags=extra_tags,
                            context_path=str(context_path) if context_path is not None else ".",
                            build_args=build_args if build_args is not None else dict(),
                            dockerfile_path=path_to_str(dockerfile_path),
                            from_git=from_git)
        self.actions.append(action)
        return action

    def exec(self,
             image_spec: ImageSpec,
             command: Optional[List[str]] = None,
             entrypoint: Optional[str] = None,
             workdir: Optional[str] = None,
             inputs: Optional[List['Input']] = None,
             outputs: Optional[List['Output']] = None) -> 'Exec':
        action = Exec(get_image_name(image_spec),
                      command = command,
                      entrypoint = entrypoint,
                      workdir=workdir,
                      inputs=inputs if inputs is not None else list(),
                      outputs=outputs if outputs is not None else list())
        self.actions.append(action)
        return action


class Exec:
    image_name: 'ImageName'
    command: Optional[List[str]]
    entrypoint: Optional[str]
    workdir: Optional[str]
    inputs: List['Input']
    outputs: List['Output']

    def __init__(self,
                 image_name: ImageName,
                 command: Optional[List[CommandElement]],
                 entrypoint: Optional[StringOrPath],
                 workdir: Optional[StringOrPath],
                 inputs: List['Input'],
                 outputs: List['Output']):
        self.image_name = image_name
        self.command = [command_element_to_str(element) for element in command] if command is not None else None
        self.entrypoint = path_to_str(entrypoint)
        self.workdir = path_to_str(workdir)
        self.inputs = inputs
        self.outputs = outputs

    #### Helpers ####
    def input(self,
              file: Optional[StringOrPath] = None,
              dir: Optional[StringOrPath] = None,
              through_file: Optional[StringOrPath] = None,
              through_dir: Optional[StringOrPath] = None,
              through_env: Optional[str] = None,
              through_stdin: bool = False) -> 'Exec':
        if file is not None:
            value = File(str(file))
        elif dir is not None:
            value = Dir(str(dir))
        else:
            raise ValueError("Input value not specified")
        if through_file is not None:
            through = ThroughFile(str(through_file))
        elif through_dir is not None:
            through = ThroughDir(str(through_dir))
        elif through_stdin:
            through = ThroughStdin()
        elif through_env is not None:
            through = ThroughEnvironment(through_env)
        else:
            # shortcut -- pass file or dir through similarly named file or dir
            if file is not None:
                through = ThroughFile(str(file))
            elif dir is not None:
                through = ThroughDir(str(dir))
            else:
                raise ValueError("Through not specified")
        input = Input(value=value, through=through)
        self.inputs.append(input)
        return self

    def output(self,
               file: StringOrPath,
               through_file: Optional[StringOrPath] = None,
               through_stdout: bool = False,
               through_stderr: bool = False) -> 'Exec':
        value = File(str(file))
        if through_file is not None:
            through = ThroughFile(str(through_file))
        elif through_stderr:
            through = ThroughStderr()
        elif through_stdout:
            through = ThroughStdout()
        else:
            # shortcut -- by default pass file through similarly named file
            through = ThroughFile(str(file))
        output = Output(value = value, through=through)
        self.outputs.append(output)
        return self


class BuildImage:
    image_name: ImageName
    context_path: str
    build_args: dict[str, str]
    dockerfile_path: Optional[str]
    from_git: Optional['FromGit']
    extra_tags: list[str]

    def __init__(self,
                 image_name: ImageName,
                 context_path: str,
                 build_args: Dict[str, str],
                 dockerfile_path: Optional[str] = None,
                 from_git: Optional['FromGit'] = None,
                 extra_tags: Optional[List[str]] = None):
        self.image_name = image_name
        self.context_path = context_path
        self.from_git = from_git
        self.dockerfile_path = dockerfile_path
        self.build_args = build_args
        self.extra_tags = extra_tags


class FromGit:
    repo: str
    rev: str

    def __init__(self, repo: str, rev: str):
        self.repo = repo
        self.rev = rev

class PullImage:
    image_name: ImageName

    def __init__(self, image_name: ImageName):
        self.image_name = image_name

class Input:
    value: Value
    through: InputThrough

    def __init__(self, value: Value, through: InputThrough):
        self.value = value
        self.through = through

class Output:
    value: Value
    through: OutputThrough

    def __init__(self, value: Value, through: OutputThrough):
        self.value = value
        self.through = through

class File:
    path: str

    def __init__(self, path: StringOrPath):
        self.path = path_to_str(path)

class Dir:
    path: str

    def __init__(self, path: StringOrPath):
        self.path = path_to_str(path)

class Image:
    image_name: ImageName

    def __init__(self, image_name: ImageName):
        self.image_name = image_name

class ThroughFile:
    path: str

    def __init__(self, path: StringOrPath):
        self.path = path_to_str(path)

class ThroughDir:
    path: str

    def __init__(self, path: StringOrPath):
        self.path = path_to_str(path)

class ThroughEnvironment:
    name: str

    def __init__(self, name: str):
        self.name = name

class ThroughStdin:
    pass

class ThroughStdout:
    pass

class ThroughStderr:
    pass

#### Utility functions ####

def get_image_name(image_spec: ImageSpec) -> ImageName:
    if isinstance(image_spec, str):
        return image_spec
    elif isinstance(image_spec, PullImage):
        return image_spec.image_name
    elif isinstance(image_spec, BuildImage):
        return image_spec.image_name
    else:
        raise ValueError(f"Unexpected image spec type {type(image_spec)}")

def path_to_str(path: Optional[StringOrPath]) -> Optional[str]:
    if path is None:
        return None
    return str(path)

def command_element_to_str(element: CommandElement) -> str:
    if isinstance(element, str):
        return element
    elif isinstance(element, File):
        return element.path
    elif isinstance(element, Dir):
        return element.path
    elif isinstance(element, PurePosixPath):
        return str(element)
    else:
        raise ValueError(f"Unexpected command element type {type(element)}")

def to_path(string_or_path: StringOrPath) -> PurePosixPath:
    if isinstance(string_or_path, str):
        return PurePosixPath(string_or_path)
    elif isinstance(string_or_path, PurePosixPath):
        return string_or_path
    else:
        raise ValueError(f"Unexpected type {type(string_or_path)}")

#### JSON serialization ####

def spec_to_json(s: Spec):
    return {
        "spec_version": f"{s.spec_version[0]}.{s.spec_version[1]}",
        "actions": list(map(action_to_json, s.actions))
    }

class WriterError(Exception):
    pass

def action_to_json(action: Action):
    if isinstance(action, PullImage):
        action_json = {"pull_image": {"image_name": action.image_name}}
        return action_json
    elif isinstance(action, BuildImage):
        action_json = {"build_image": {
            "image_name": action.image_name,
            "context_path": action.context_path,
        }}
        if action.dockerfile_path:
            action_json['build_image']['dockerfile_path'] = action.dockerfile_path
        if action.build_args:
            action_json['build_image']['build_args'] = [{"name": key, "value": value} for (key, value) in action.build_args.items()]
        if action.from_git:
            action_json['build_image']['from_git'] = {"repo": action.from_git.repo, "rev": action.from_git.rev}
        if action.extra_tags:
            action_json['build_image']['extra_tags'] = action.extra_tags
        return action_json
    elif isinstance(action, Exec):
        action_json = {"exec": {
            "image_name": action.image_name
        }}
        if action.command:
            action_json['exec']['command'] = action.command
        if action.entrypoint:
            action_json['exec']['entrypoint'] = action.entrypoint
        if action.workdir:
            action_json['exec']['workdir'] = action.workdir
        if len(action.inputs) > 0:
            action_json['exec']['inputs'] = list(map(input_to_json, action.inputs))
        if len(action.outputs) > 0:
            action_json['exec']['outputs'] = list(map(output_to_json, action.outputs))
        return action_json
    else:
        raise WriterError(f"Unexpected action type {type(action)}")

def input_to_json(input: Input):
    through = input.through
    if isinstance(through, ThroughFile):
        through_json = {"file": {"path": through.path}}
    elif isinstance(through, ThroughDir):
        through_json = {"dir": {"path": through.path}}
    elif isinstance(through, ThroughStdin):
        through_json = {"stream": {"name": "STDIN"}}
    elif isinstance(through, ThroughEnvironment):
        through_json = {"environment": {"name": through.name}}
    else:
        raise WriterError(f"Unexpected input through type {type(through)}")
    return {"value": value_to_json(input.value), "through": through_json}

def output_to_json(output: Output):
    through = output.through
    if isinstance(through, ThroughFile):
        through_json = {"file": {"path": through.path}}
    elif isinstance(through, ThroughDir):
        through_json = {"dir": {"path": through.path}}
    elif isinstance(through, ThroughStdout):
        through_json = {"stream": {"name": "STDOUT"}}
    elif isinstance(through, ThroughStderr):
        through_json = {"stream": {"name": "STDERR"}}
    else:
        raise WriterError(f"Unexpected output through type {type(through)}")
    return {"value": value_to_json(output.value), "through": through_json}

def value_to_json(value: Value):
    if isinstance(value, File):
        return {"file": {"path": value.path}}
    elif isinstance(value, Dir):
        return {"dir": {"path": value.path}}
    else:
        raise WriterError(f"Unexpected value type {type(value)}")

def print_spec_json(s: Spec):
    json.dump(spec_to_json(s), sys.stdout)

