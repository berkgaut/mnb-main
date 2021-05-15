from mnb.builder import Plan
import unittest


class PlanBuilderTest(unittest.TestCase):

    def test_simple_plan(self):
        plan = Plan()
        image_foo = plan.image("foo").from_registry()
        src_file_a = plan.file("source_A") #, through_file="foo_input_file", through_stdin=False, through_env=False, preprocessor=None)
        dst_file_b = plan.file("file_B") #, through_file="foo_output_file")
        plan.exec(image_foo, ["echo", "foo"],
                         inputs=[src_file_a.as_input()],
                         outputs=[dst_file_b.as_output()])
        src_file_b = plan.file("file_B") #, through_file="bar_input_file")
        dst_file_c = plan.file("file_C") #, through_file="bar_output_file")
        image_bar = plan.image("bar").from_context("containers/bar")
        aws_creds = plan.file(".aws/credentials", secret=True).as_input()
        aws_config = plan.file(".aws/config", secret=True).as_input()
        plan.exec(image_bar, ["bar", src_file_b.as_input(through_path="src")],
                         outputs=[dst_file_c.as_output()], entrypoint="entrypoint").input(aws_creds).input(aws_config)



