from typing import Union, Optional, Tuple, Dict, List

ImageName = str
Action = Union['PullImage', 'BuildImage', 'Exec']
Value = Union['File', 'Dir', 'Image']
InputThrough = Union['ThroughFile', 'ThroughDir', 'ThroughEnvironment', 'ThroughStdin']
OutputThrough = Union['ThroughFile', 'ThroughDir', 'ThroughStdout', 'ThroughStderr']

class Spec:
    spec_version: Tuple[int, int]
    actions: List['Action']

    def __init__(self, spec_version: Tuple[int, int], actions: List['Action']):
        self.spec_version = spec_version
        self.actions = actions

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

class BuildImage:
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
    def __init__(self, repo: str, rev: str):
        self.repo = repo
        self.rev = rev

class PullImage:
    def __init__(self, image_name: ImageName):
        self.image_name = image_name

class Input:
    def __init__(self, value: Value, through: InputThrough):
        self.value = value
        self.through = through

class Output:
    def __init__(self, value: Value, through: OutputThrough):
        self.value = value
        self.through = through

class File:
    def __init__(self, path: str):
        self.path = path

class Dir:
    def __init__(self, path: str):
        self.path = path

class Image:
    def __init__(self, image_name: str):
        self.image_name = image_name

class ThroughFile:
    def __init__(self, path: str):
        self.path = path

class ThroughDir:
    def __init__(self, path: str):
        self.path = path

class ThroughEnvironment:
    def __init__(self, name: str):
        self.name = name

class ThroughStdin:
    pass

class ThroughStdout:
    pass

class ThroughStderr:
    pass

