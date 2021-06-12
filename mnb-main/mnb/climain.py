import logging
import os, sys
import argparse
from inspect import signature
from pathlib import PureWindowsPath, PurePosixPath, Path
from typing import Callable, Any

import docker

from mnb.builder import Plan
from mnb.executor import Context, PlanExecutor
from mnb.state import State
from mnb.version import MNB_VERSION

def build_plan(planf: Callable[[Plan], Any]) -> Plan:
    builder = Plan()
    planf(builder)
    return builder

def create_context(absroot_path):
    client = docker.from_env()
    state_path = Path(absroot_path) / ".mnb-state.sqlite"
    state = State(str(state_path))
    context = Context(client, state, absroot_path)
    return context

def get_abs_root_path(ns):
    if not ns.rootabspath:
        rootabspath = os.getcwd()
        logging.log(logging.WARN, "--rootabspath not specified, assuming %s", rootabspath)
        logging.log(logging.WARN, "running without --rootabspath only works outside of container")
    else:
        rootabspath = ns.rootabspath
    if ns.windows_host:
        absroot_path = PureWindowsPath(rootabspath)
    else:
        absroot_path = PurePosixPath(rootabspath)
    if not absroot_path.is_absolute():
        logging.log(logging.ERROR, "--contextpath should be an absolute path: %s", absroot_path)
        exit(1)
    return absroot_path


def update(ns, planf):
    plan = build_plan(planf)
    context = create_context(get_abs_root_path(ns))
    try:
        executor = PlanExecutor(plan)
        executor.update(context)
    finally:
        context.close()

def clean(ns, planf):
    plan = build_plan(planf)
    context = create_context(get_abs_root_path(ns))
    try:
        executor = PlanExecutor(plan)
        executor.clean(context)
    finally:
        context.close()

def showplan(ns, planf):
    plan = build_plan(planf)
    executor = PlanExecutor(plan)
    executor.showplan(sys.stdout)

def argparse_test(ns):
    print(ns)

def run_extension(ns, plan_builder):
    # TODO
    pass

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
    root_parser.add_argument('--debug', action='store_true', help="Debug mode")

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

    if root_ns.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    n_func_params = len(signature(root_ns.func).parameters)
    if n_func_params == 1:
        root_ns.func(root_ns)
    elif n_func_params == 2:
        # execute plan file and get build_plan function
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
