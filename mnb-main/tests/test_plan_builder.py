from mnb.builder import Plan
import unittest

class PlanBuilderTest(unittest.TestCase):

    def assertJsonPreservesPlan(self, plan):
        json = plan.to_json()
        from pprint import pprint
        pprint(json)
        self.assertEqual(json, Plan.from_json(json).to_json())

    def test_all_plan_elements(self):
        plan = Plan()
        image_foo = plan.pull_image("foo")
        plan.exec(image_foo, ["/bin/sh", "-c", "echo aaa"])
        self.assertJsonPreservesPlan(plan)

    def test_empty_plan(self):
        self.assertJsonPreservesPlan(Plan())

    def test_build(self):
        plan = Plan()
        plan.build_image("foo", "path/to/context")
        self.assertJsonPreservesPlan(plan)

    def test_exec(self):
        plan = Plan()
        file_a = plan.file("A")
        file_b = plan.file("B")
        plan.exec(plan.pull_image("foo"), ["aaa"],
                  inputs=[file_a.as_input(through_path="AAA"), file_a.through_stdin(), file_a.through_env("VAR")],
                  outputs=[file_b.as_output(), file_b.through_stderr(), file_b.through_stdout()],
                  entrypoint="/docker/entrypoint.sh")
        self.assertJsonPreservesPlan(plan)
