import json
import sys
from pathlib import PosixPath

import marko
from marko.ast_renderer import ASTRenderer

from spec import *
from spec_json import print_spec_json

s = Spec(spec_version=(1, 0))

file_path = PosixPath("examples/python-with-extras") / "example.md"

with file_path.open("r") as file:
    ast = marko.parse(file.read())
    render = ASTRenderer()
    json.dump(render.render(ast), indent=2, fp=sys.stderr)

    # get options encoded in link def syntax
    generated_dir = ast.link_ref_defs.get("mnb-graphviz:generated_dir", ("generated", None))[0]

    image_list = []

    for (id, link_def) in ast.link_ref_defs.items():
        if id.startswith("mnb-graphviz:"):
            # option
            continue
        dest, title = link_def
        if str((file_path.parent / dest).parent) == generated_dir:
            image_list.append(dest)






print_spec_json(s)