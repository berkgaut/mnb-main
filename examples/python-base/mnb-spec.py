from spec import *
from spec_json import print_spec_json

s = Spec(spec_version=(1, 0), actions=[])
pull_image_foo = PullImage("foo")
s.actions.append(pull_image_foo)
build_image_bar = BuildImage("bar", context_path="containers/bar", build_args={})
s.actions.append(build_image_bar)
foo_a_to_b = Exec(image_name="foo", inputs=[Input(value=File("a"), through=ThroughFile("a"))],
                  outputs=[Output(value=File("b"), through=ThroughFile("b"))], command=["convert", "a", "b"],
                  entrypoint=None, workdir=None)
s.actions.append(foo_a_to_b)
bar_b_to_c = Exec(image_name="bar", inputs=[Input(value=File("b"), through=ThroughFile("b"))],
                  outputs=[Output(value=File("c"), through=ThroughFile("c"))], command=["postprocess", "b", "c"],
                  entrypoint=None, workdir=None)
s.actions.append(bar_b_to_c)

print_spec_json(s)