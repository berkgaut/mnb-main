from spec import *
from spec_json import *
import sys

# Note that the output is sent to stderr, as stdout is used to output spec JSON
print("Hello from Python script which uses Pythjon DSL to generate mnb spec!", file=sys.stderr)

s = Spec(spec_version=(1, 0), description="python-base example")

GRAPHVIZ="trivial-graphviz"

s.build_image(GRAPHVIZ,
              context_path="containers/graphviz",
              from_git=FromGit(repo="https://github.com/berkgaut/mnb-main.git", rev="master"))

def dot2png(s: Spec, source: [str, PurePosixPath], output: [str, PurePosixPath]):
    source_path = PurePosixPath(source)
    output_path = PurePosixPath(output)
    s.exec(image_name=GRAPHVIZ,
           inputs=[Input(value=File(str(source_path)), through=ThroughFile(source_path.name))],
           outputs=[Output(value=File(str(output_path)), through=ThroughFile(output_path.name))],
           command=["dot", "-Tpng", "-o", str(output_path.name), str(source_path.name)])

dot2png(s, "example.dot", "mnb-generated/example.png")

print_spec_json(s)
