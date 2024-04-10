import sys
from pathlib import PosixPath

from mistletoe import Document
from mistletoe.ast_renderer import ASTRenderer

from spec import *
from spec_json import print_spec_json

s = Spec(spec_version=(1, 0))

file_path = PosixPath("examples/python-with-extras") / "example.md"

with file_path.open("r") as file:
    ast = Document(file)
    renderer = ASTRenderer()
    print(renderer.render(ast), file=sys.stderr)

print_spec_json(s)