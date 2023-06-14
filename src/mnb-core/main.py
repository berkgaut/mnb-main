import argparse
import sys
from pathlib import PureWindowsPath, PurePosixPath, WindowsPath, PosixPath

import docker_executor

def update(ns):
    docker_executor.h(ns)

def main():
    root_parser = argparse.ArgumentParser(prog='mnb')
    root_parser.add_argument('--rootabspath', nargs='?', help="Absolute path to working context on host machine")
    root_parser.add_argument('--config-file', '-f', dest='config_file', help="Path to config file", default=None)
    root_parser.add_argument('--windows-host', action='store_true', help="host machine is running Windows "
                                                                         "(by default a Unix-like system is assumed)")
    root_parser.add_argument('--dev-mode', action='store_true', help="Development mode (run outside of a container)")
    subparsers = root_parser.add_subparsers(dest='subcommand')
    update_parser = subparsers.add_parser('update', help='perform actions to update values')

    ns = root_parser.parse_args(sys.argv[1:])

    if ns.windows_host:
        host_pure_path_class = PureWindowsPath
        host_path_class = WindowsPath
    else:
        host_pure_path_class = PurePosixPath
        host_path_class = PosixPath

    ns.context_absolute_path_on_host = host_pure_path_class(ns.rootabspath)

    if ns.dev_mode:
        ns.context_absolute_path_for_mnb = host_path_class(ns.rootabspath)
    else:
        ns.context_absolute_path_for_mnb = PosixPath("/mnb/run")

    if ns.config_file:
        ns.config_file_path = ns.context_absolute_path_for_mnb / ns.config_file
    else:
        ns.config_file_path = None

    if not ns.subcommand or ns.subcommand == 'update':
        update(ns)

if __name__ == "__main__":
    main()
