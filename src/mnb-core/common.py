from pathlib import Path
from typing import Optional


def get_lib_path() -> Path:
    return Path(__file__).parent / "lib"

class CommandLineOptions:
    rootabspath: Optional[str]
    #config_file: str
    windows_host: bool
    dev_mode: bool
    subcommand: Optional[str]
