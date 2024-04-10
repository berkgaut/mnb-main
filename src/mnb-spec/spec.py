from pathlib import PurePosixPath
from typing import Union, Optional, Tuple, Dict, List

ImageName = str
Action = Union['PullImage', 'BuildImage', 'Exec']
Value = Union['File', 'Dir', 'Image']
InputThrough = Union['ThroughFile', 'ThroughDir', 'ThroughEnvironment', 'ThroughStdin']
OutputThrough = Union['ThroughFile', 'ThroughDir', 'ThroughStdout', 'ThroughStderr']

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

    #### Helpers ####
    def pull_image(self, image_name: ImageName) -> 'PullImage':
        action = PullImage(image_name)
        self.actions.append(action)
        return action

    def build_image(self,
                    image_name: ImageName,
                    context_path: Optional[StringOrPath] = None,
                    build_args: Optional[dict[str, str]] = None,
                    dockerfile_path: Optional[str] = None,
                    from_git: Optional['FromGit'] = None) -> 'BuildImage':
        action = BuildImage(image_name,
                            context_path=str(context_path) if context_path is not None else ".",
                            build_args=build_args if build_args is not None else dict(),
                            dockerfile_path=dockerfile_path,
                            from_git=from_git)
        self.actions.append(action)
        return action

    def exec(self,
             image_name: ImageName,
             command: Optional[List[str]] = None,
             entrypoint: Optional[str] = None,
             workdir: Optional[str] = None,
             inputs: Optional[List['Input']] = None,
            outputs: Optional[List['Output']] = None) -> 'Exec':
        action = Exec(image_name,
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
                 command: Optional[List[str]],
                 entrypoint: Optional[str],
                 workdir: Optional[str],
                 inputs: List['Input'],
                 outputs: List['Output']):
        self.image_name = image_name
        self.command = command
        self.entrypoint = entrypoint
        self.workdir = workdir
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

    def __init__(self,
                 image_name: ImageName,
                 context_path: str,
                 build_args: Dict[str, str],
                 dockerfile_path: Optional[str] = None,
                 from_git: Optional['FromGit'] = None):
        self.image_name = image_name
        self.context_path = context_path
        self.from_git = from_git
        self.dockerfile_path = dockerfile_path
        self.build_args = build_args


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

    def __init__(self, path: str):
        self.path = path

class Dir:
    path: str

    def __init__(self, path: str):
        self.path = path

class Image:
    image_name: ImageName

    def __init__(self, image_name: ImageName):
        self.image_name = image_name

class ThroughFile:
    path: str

    def __init__(self, path: str):
        self.path = path

class ThroughDir:
    path: str

    def __init__(self, path: str):
        self.path = path

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
