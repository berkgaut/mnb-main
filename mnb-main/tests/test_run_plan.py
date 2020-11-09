import docker

from mnb.plan import Plan, Context
from mnb.state import State


import unittest
import os

class PlanExecutionTest(unittest.TestCase):

    def test_run(self):
        abs_root_path = os.getcwd()
        plan = Plan(absroot_path=abs_root_path)

        image_bash = plan.registry_image("bash")

        src_a = plan.src_file("mnb-main/tests/test_files/source_A",
                              through_file="input_file_A",
                              through_stdin=False,
                              through_env=False,
                              preprocessor=None)
        src_b = plan.src_file("mnb-main/tests/test_files/source_B",
                              through_file="input_file_B",
                              through_stdin=True,
                              through_env=False,
                              preprocessor=None)
        dst_file = plan.dst_file("mnb-main/tests/test_files/result", through_stdout=True)
        plan.transform([src_a, src_b], [dst_file], image_bash, ["cat", src_a.workpath(), src_b.workpath()])
        client = docker.from_env()
        context = Context(client, State("mnb-main/tests/test_files/.mnb-state"))
        plan.update(context)
        context.close()
        with open("mnb-main/tests/test_files/result", "r") as f:
            self.assertEqual(f.read(), "AAABBB")


    @unittest.skip("FIXME: this test hangs")
    def test_run_2(self):
        result_path = "mnb-main/tests/test_files/result"

        os.unlink(result_path)
        abs_root_path = os.getcwd()
        plan = Plan(absroot_path=abs_root_path)

        image_bash = plan.registry_image("bash")

        src_a = plan.src_file("mnb-main/tests/test_files/source_A",
                              through_file=None,
                              through_stdin=True,
                              through_env=False,
                              preprocessor=None)
        src_b = plan.src_file("mnb-main/tests/test_files/source_B",
                              through_file="input_file_B",
                              through_stdin=True,
                              through_env=False,
                              preprocessor=None)
        dst_file = plan.dst_file(result_path, through_stdout=True)
        plan.transform([src_a, src_b], [dst_file], image_bash, ["cat", "-", src_b.workpath()])
        client = docker.from_env()
        context = Context(client, State("mnb-main/tests/test_files/.mnb-state"))
        plan.update(context)
        context.close()
        with open(result_path, "r") as f:
            self.assertEqual(f.read(), "AAABBB")

    

