from spec import *
from spec_json import print_spec_json
import marko

s = Spec(spec_version=(1, 0))
s.pull_image("foo")
s.build_image("bar", context_path="containers/bar")

x2y = s.exec("foo", command=["convert", "input", "output"])
x2y.input(file="x", through_file="input")
x2y.output(file="y", through_file="output")

s.exec("bar", command=["postprocess", "y", "z"]).input(file="y").output(file="z")

print_spec_json(s)