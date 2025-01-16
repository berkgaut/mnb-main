import argparse
import sys

import executor
from common import CommandLineOptions

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
    init_parser = subparsers.add_parser('init', help='initialize a new project in the current directory')
    scripts_parser = subparsers.add_parser('scripts', help='update scripts')

    cliopts = root_parser.parse_args(args=sys.argv[1:], namespace=CommandLineOptions())

    if not cliopts.subcommand:
        if cliopts.rootabspath:
            # started from script, display regular help
            root_parser.print_help()
            sys.exit(1)
        else:
            # started via docker run, display initial help
            print_initial_help()
            sys.exit(0)

    elif cliopts.subcommand == 'update':
        executor.update(cliopts)
    elif cliopts.subcommand == 'init':
        executor.init(cliopts)
    elif cliopts.subcommand == 'scripts':
        executor.scripts(cliopts)

def print_initial_help():
    print("To create mnb workspace and startup scripts, run:")
    print("  docker run -v $(pwd):/mnb/run --rm bberkgaut/mnb:latest init")

if __name__ == "__main__":
    main()
