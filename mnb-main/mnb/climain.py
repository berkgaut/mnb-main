import os
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

def argparse_test(ns):
    print(ns)

def run_extension(ns, plan_builder):
    p = mkplan(ns, plan_builder)
    print("run extension: %s", ns.extension_args)

def scripts(ns):
    if ns.dev_mode:
        src_dir_path = Path("scripts")
        dst_dir_path = Path(".")
    else:
        from pathlib import PosixPath
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
    cmdline_args = sys.argv[1:]

    root_parser = argparse.ArgumentParser(prog='mnb')
    root_parser.add_argument('--rootabspath', nargs='?', help="Absolute path to working context on host machine")
    root_parser.add_argument('--windows-host', action='store_true', help="host machine is running Windows (by default Unix-like system is assumed)")
    root_parser.add_argument('--plan-file', default="mnb-plan.py", help="path to plan description")
    root_parser.add_argument('--dev-mode', action='store_true', help="Development mode (run outside of a container)")

    root_ns, rest = root_parser.parse_known_args(cmdline_args)

    if len(rest) == 0:
        # default action: update
        root_ns.func = update
    elif rest[0] == "update":
        root_ns.func = update
    elif rest[0] == "clean":
        root_ns.func = clean
    elif rest[0] == "showplan":
        root_ns.func = showplan
    elif rest[0] == "scripts":
        root_ns.func = scripts
    elif rest[0] == "argparse-test":
        root_ns.func = argparse_test
    else:
        root_ns.func = run_extension
        root_ns.extension_args = rest

    n_func_params = len(signature(root_ns.func).parameters)
    if n_func_params == 1:
        root_ns.func(root_ns)
    elif n_func_params == 2:
        plan_file_path = Path(root_ns.plan_file)
        if not plan_file_path.exists():
            raise Exception("Plan file %s does not exist" % plan_file_path)
        plan_env = dict()
        exec(plan_file_path.open("r").read(), plan_env)
        BUILD_PLAN = 'build_plan'
        if not BUILD_PLAN in plan_env:
            raise Exception("Function %s not defined in plan file %s" % (BUILD_PLAN, plan_file_path))
        plan_builder = plan_env[BUILD_PLAN]
        root_ns.func(root_ns, plan_builder)

if __name__=="__main__":
    main()
