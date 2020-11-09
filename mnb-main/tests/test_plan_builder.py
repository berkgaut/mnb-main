from mnb.plan import Plan
import unittest


class PlanBuilderTest(unittest.TestCase):

    def test_simple_plan(self):
        plan = Plan(absroot_path="/rootabspath")
        image_foo = plan.registry_image("foo")
        src_file_a = plan.src_file("source_A", through_file="foo_input_file", through_stdin=False, through_env=False, preprocessor=None)
        dst_file_b = plan.dst_file("file_B", through_file="foo_output_file")
        tf_1 = plan.transform([src_file_a], [dst_file_b], image_foo, ["echo", "foo"])
        src_file_b = plan.src_file("file_B", through_file="bar_input_file")
        dst_file_c = plan.dst_file("file_C", through_file="bar_output_file")
        image_bar = plan.registry_image("bar")
        tf_2 = plan.transform([src_file_b], [dst_file_c], image_bar, ["echo", "bar"])
        tt = plan.runlist()
        self.assertEqual(tt[0], tf_1)
        self.assertEqual(tt[1], tf_2)



