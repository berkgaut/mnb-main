import os
import sys
import argparse
from inspect import signature
from pathlib import PureWindowsPath

import docker
from mnb.plan import *
from mnb.log import INFO, WARN, ERROR
from mnb.version import MNB_VERSION

def mkplan(ns, plan_builder):
    if not ns.rootabspath:
        rootabspath = os.getcwd()
        WARN("--rootabspath not specified, assuming " + rootabspath)
        WARN("running without --rootabspath only works outside of container")
    else:
        rootabspath = ns.rootabspath
    if ns.windows_host:
        absroot_path = PureWindowsPath(rootabspath)
    else:
        absroot_path = PurePosixPath(rootabspath)
    if not absroot_path.is_absolute():
        ERROR("--contextpath should be an absolute path: %s" % absroot_path)
        exit(1)
    plan = Plan(absroot_path=absroot_path)
    return plan_builder(plan)

def update(ns, plan_builder):
    p = mkplan(ns, plan_builder)
    client = docker.from_env()
    state = State()
    p.update(client, state)

def clean(ns, plan_builder):
    p = mkplan(ns, plan_builder)
    p.clean()

def showplan(ns, plan_builder):
    p = mkplan(ns, plan_builder)
    p.show()

def scripts(ns):
    if ns.dev_mode:
        src_dir_path = Path("scripts")
        dst_dir_path = Path(".")
    else:
        src_dir_path = PosixPath("/mnb/lib/scripts")
        dst_dir_path = PosixPath("/mnb/run")
    for name, overwrite, setx in [("mnb", True, True),
                                  ("mnb.cmd", True, False),
                                  ("mnb-plan.py", False, False)]:
        if (dst_dir_path / name).exists() and not overwrite:
            continue
        with (src_dir_path / name).open("r") as i:
            if dst_dir_path.is_dir():
                with (dst_dir_path / name).open("w") as o:
                    c = i.read().replace("MNB_VERSION", MNB_VERSION)
                    o.write(c)
                if setx:
                    Path(dst_dir_path / name).chmod(0o755)

def main():
    parser = argparse.ArgumentParser(prog='mnb')
    parser.add_argument('--rootabspath', nargs='?', help="Absolute path to working context on host machine")
    parser.add_argument('--windows-host', action='store_true', help="host machine is running Windows (by default Unix-like system is assumed)")
    parser.add_argument('--argparse-test', action='store_true', help="dry run, print command-line parsing result")
    parser.add_argument('--plan-file', default="mnb-plan.py", help="path to plan description")
    parser.add_argument('--dev-mode', action='store_true', help="Development mode (run outside of a container)")
    parser.set_defaults(func=update)
    subparsers = parser.add_subparsers()

    parser_update = subparsers.add_parser("update")
    parser_update.set_defaults(func=update)

    parser_clean = subparsers.add_parser("clean")
    parser_clean.set_defaults(func=clean)

    parser_showplan = subparsers.add_parser("showplan")
    parser_showplan.set_defaults(func=showplan)

    parser_scripts = subparsers.add_parser("scripts")
    parser_scripts.set_defaults(func=scripts)

    ns = parser.parse_args(sys.argv[1:])
    if ns.argparse_test:
        print(ns)
        exit(0)
    else:
        n_args = len(signature(ns.func).parameters)
        if n_args == 1:
            ns.func(ns)
        elif n_args == 2:
            plan_file_path = Path(ns.plan_file)
            if not plan_file_path.exists():
                raise Exception("Plan file %s does not exist" % plan_file_path)
            plan_env = dict()
            exec(plan_file_path.open("r").read(), plan_env)
            BUILD_PLAN = 'build_plan'
            if not BUILD_PLAN in plan_env:
                raise Exception("Function %s not defined in plan file %s" % (BUILD_PLAN, plan_file_path))
            plan_builder = plan_env[BUILD_PLAN]
            ns.func(ns, plan_builder)

if __name__=="__main__":
    main()