import json
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

def create_context(absroot_path):
    from mnb.executor import MNB_DIR, ensure_writable_dir
    client = docker.from_env()
    mnb_dir = Path(absroot_path) / MNB_DIR
    ensure_writable_dir(mnb_dir)
    state_path = mnb_dir / "mnb-state.sqlite"
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


def update(ns, plan, always_run_last=False):
    context = create_context(get_abs_root_path(ns))
    try:
        executor = PlanExecutor(plan)
        return executor.update(context, always_run_last)
    finally:
        context.close()

def clean(ns, plan):
    context = create_context(get_abs_root_path(ns))
    try:
        executor = PlanExecutor(plan)
        executor.clean(context)
    finally:
        context.close()

def showplan(ns, plan):
    executor = PlanExecutor(plan)
    executor.showplan(sys.stdout)

def dump_plan(ns, plan):
    executor = PlanExecutor(plan)
    executor.dump_plan(sys.stdout)

def argparse_test(ns):
    print(ns)

def dumpstate(ns):
    context = create_context(get_abs_root_path(ns))
    context.state_storage.dump(sys.stdout)

def run_extension(ns, plan):
    # TODO
    pass

def scripts(ns):
    if ns.dev_mode:
        src_dir_path = Path("mnb-main/scripts")
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
    root_parser.add_argument('--mnb-file', default="mnb-plan.json", help="path to mnb plan file")
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
    elif rest[0] == "dumpplan":
        root_ns.func = dump_plan
    elif rest[0] == "scripts":
        root_ns.func = scripts
    elif rest[0] == "argparse-test":
        root_ns.func = argparse_test
    elif rest[0] == "dumpstate":
        root_ns.func = dumpstate
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
        mnb_file_path = Path(root_ns.mnb_file)
        if not mnb_file_path.exists():
            raise Exception("Plan file %s does not exist" % mnb_file_path)
        with mnb_file_path.open("r") as mnb_file:
            metaplan_data = json.loads(mnb_file.read())
            metaplan = Plan.from_json(metaplan_data)
            metaplan_result = update(root_ns, metaplan, always_run_last=True)
            if metaplan_result.exit_code != 0:
                raise Exception
            plan_data = json.loads(metaplan_result.stdout_bytes)
            plan = Plan()
            plan.from_json(plan_data)
            root_ns.func(root_ns, plan)

if __name__=="__main__":
    main()
