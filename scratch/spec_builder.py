from pathlib import PurePosixPath

from spec import *

PathLike = Union[str, PurePosixPath]

class SpecBuilderBase:
    def spec_version(self, major: int, minor: int) -> 'SpecBuilderBase':
        raise NotImplementedError()

    def pull_image(self, image_name: str) -> 'PullImageBuilderBase':
        raise NotImplementedError()

    def build_image(self, image_name: str) -> 'BuildImageBuilderBase':
        raise NotImplementedError()


class PullImageBuilderBase:
    image_name: str

    def __init__(self, image_name: str):
        self.image_name = image_name


class BuildImageBuilderBase:
    image_name: str

    def __init__(self, image_name: str):
        self.image_name = image_name

    def context_path(self, path: PathLike) -> 'BuildImageBuilderBase':
        raise NotImplementedError()

    def dockerfile_path(self, path: PathLike) -> 'BuildImageBuilderBase':
        raise NotImplementedError()

    def build_args(self, args: Dict[str, str]) -> 'BuildImageBuilderBase':
        raise NotImplementedError()

    def from_git(self, repo: str, rev: Optional[str] = None) -> 'BuildImageBuilderBase':
        raise NotImplementedError()


class ExecBuilderBase:
    image_name: str

    def __init__(self, image_name: str):
        self.image_name = image_name

    def command(self, command):
        raise NotImplementedError()

    def entrypoint(self, entrypoint: PathLike):
        raise NotImplementedError()

    def workdir(self, workdir: PathLike):
        raise NotImplementedError

    def input_through_file(self, path: PathLike):
        raise NotImplementedError()



    # image_name: 'ImageName'
    # command: Optional[List[str]]
    # entrypoint: Optional[str]
    # workdir: Optional[str]
    # inputs: List['Input']
    # outputs: List['Output']

