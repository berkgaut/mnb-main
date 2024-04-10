import argparse
import sys

import executor
from common import CommandLineOptions

def update(cliopts: CommandLineOptions):
    executor.update(cliopts)

def main():
    root_parser = argparse.ArgumentParser(prog='mnb')
    root_parser.add_argument('--rootabspath', dest='rootabspath', nargs='?',
                             help="Absolute path to working context on host machine")
    # root_parser.add_argument('--config-file', '-f', dest='config_file', default="mnb.json",
    #                          help="Path to config file")
    root_parser.add_argument('--windows-host', dest="windows_host", action='store_true',
                             help="host machine is running Windows (by default a Unix-like system is assumed)")
    root_parser.add_argument('--dev-mode', dest="dev_mode", action='store_true',
                             help="Development mode (run outside of a container)")
    subparsers = root_parser.add_subparsers(dest='subcommand')
    update_parser = subparsers.add_parser('update', help='perform actions to update values')

    cliopts = root_parser.parse_args(args=sys.argv[1:], namespace=CommandLineOptions())

    if not cliopts.subcommand or cliopts.subcommand == 'update':
        update(cliopts)

if __name__ == "__main__":
    main()
