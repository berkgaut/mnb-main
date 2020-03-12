import os
import sys
import argparse
from pathlib import PureWindowsPath

import docker
from mnb.plan import *
from mnb.log import INFO, WARN, ERROR

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

def main(plan_builder):
    parser = argparse.ArgumentParser(prog='mnb')
    parser.add_argument('--rootabspath', nargs='?', help="Absolute path to working context on host machine")
    parser.add_argument('--windows-host', action='store_true', help="host machine is running Windows (by default Unix-like system is assumed)")
    parser.add_argument('--argparse-test', action='store_true', help="dry run, print command-line parsing result")
    parser.set_defaults(func=update)
    subparsers = parser.add_subparsers()

    parser_update = subparsers.add_parser("update")
    parser_update.set_defaults(func=update)

    parser_clean = subparsers.add_parser("clean")
    parser_clean.set_defaults(func=clean)

    parser_clean = subparsers.add_parser("showplan")
    parser_clean.set_defaults(func=showplan)

    ns = parser.parse_args(sys.argv[1:])
    if ns.argparse_test:
        print(ns)
        exit(0)
    else:
        ns.func(ns, plan_builder)
