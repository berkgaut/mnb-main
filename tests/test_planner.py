import unittest

from spec import *
from plan import toposort_actions

class Test(unittest.TestCase):
    def test_spec_from_scratch(self):
        s = Spec(spec_version=(1,0), actions=[])
        pull_image_foo = PullImage("foo")
        s.actions.append(pull_image_foo)
        build_image_bar = BuildImage("bar", context_path="containers/bar", build_args={})
        s.actions.append(build_image_bar)
        foo_a_to_b = Exec(image_name="foo", inputs=[Input(value=File("a"), through=ThroughFile("a"))],
                 outputs=[Output(value=File("b"), through=ThroughFile("b"))], command=["convert", "a", "b"],
                 entrypoint=None)
        s.actions.append(foo_a_to_b)
        bar_b_to_c = Exec(image_name="bar", inputs=[Input(value=File("b"), through=ThroughFile("b"))],
                 outputs=[Output(value=File("c"), through=ThroughFile("c"))], command=["postprocess", "b", "c"],
                 entrypoint=None)
        s.actions.append(bar_b_to_c)
        planned_actions = toposort_actions(s)
        print(planned_actions)
        self.assertEqual(len(planned_actions), 4)
        self.assertTrue(self.preceedes(pull_image_foo, foo_a_to_b, planned_actions))
        self.assertTrue(self.preceedes(build_image_bar, bar_b_to_c, planned_actions))
        self.assertTrue(self.preceedes(foo_a_to_b, bar_b_to_c, planned_actions))

    def preceedes(self, a1, a2, planned_actions):
        i1 = planned_actions.index(a1)
        i2 = planned_actions.index(a2)
        return i1 < i2
