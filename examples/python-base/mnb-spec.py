from spec import *
from spec_json import print_spec_json

s = Spec(spec_version=(1, 0), description="python-base examnple")

GRAPHVIZ="trivial-graphviz"

s.build_image(GRAPHVIZ, context_path="containers/graphviz")

def dot2png(s: Spec, source: [str, PurePosixPath], output: [str, PurePosixPath]):
    source_path = PurePosixPath(source)
    output_path = PurePosixPath(output)
    s.exec(image_name=GRAPHVIZ,
           inputs=[Input(value=File(str(source_path)), through=ThroughFile(source_path.name))],
           outputs=[Output(value=File(str(output_path)), through=ThroughFile(output_path.name))],
           command=["dot", "-Tpng", "-o", str(output_path.name), str(source_path.name)])

dot2png(s, "examples/python-base/example.dot", "examples/python-base/mnb-generated/example.png")

print_spec_json(s)