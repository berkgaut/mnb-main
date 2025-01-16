import json
import re
import sys
from pathlib import PosixPath

import marko
from marko.ast_renderer import ASTRenderer
from marko.renderer import Renderer

# from spec import *
# from spec_json import print_spec_json
#
# s = Spec(spec_version=(1, 0))


def collect_elements(subtree_root, predicate):
    result = list()

    def walk_subtree(subtree_root):
        if hasattr(subtree_root, "children") and isinstance(subtree_root.children, list):
            for child in subtree_root.children:
                if hasattr(child, "get_type") and predicate(child):
                    result.append(child)
                else:
                    walk_subtree(child)

    walk_subtree(subtree_root)
    return result


def collect_options(document, ns):
    predicate = lambda element: element.get_type() == "LinkRefDef" and element.label == ns
    elements = collect_elements(document, predicate)
    def unquote_value(s: str):
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s
    return {element.dest: unquote_value(element.title) for element in elements}

"""
collect Image elements
"""
def collect_images(document, document_path):
    predicate = lambda element: element.get_type() == "Image"
    elements = collect_elements(document, predicate)
    return { str(document_path / element.dest): element for element in elements }

"""
all code blocks with mnb.reify attribute
"""
def collect_embedded_files(document, document_path):
    predicate = lambda element: element.get_type() == "FencedCode"

    def parse_key_value_pairs(s):
        pattern = re.compile(r'(\w+)=("[^"]*"|\S+)')
        matches = pattern.findall(s)
        return {key: value.strip('"') for key, value in matches}
    def generator():
        for element in collect_elements(document, predicate):
            print(element.lang)
            print(element.extra)
            if hasattr(element, 'extra'):
                element.code_attrs = parse_key_value_pairs(element.info)
                if "mnb.reify" in element.code_attrs:
                    yield element
    return list(generator())


file_path = PosixPath(".") / "example.md"

with file_path.open("r") as file:
    ast = marko.parse(file.read())
    render = ASTRenderer()
    # json.dump(render.render(ast), indent=2, fp=sys.stdout)

    options = collect_options(ast, "mnb-graphviz.option")
    print(options)
    embedded_files = collect_embedded_files(ast, file_path)
    print(embedded_files)

    # get options encoded in link def syntax
    # generated_dir = ast.link_ref_defs.get("mnb-graphviz:generated_dir", ("generated", None))[0]
    #
    # image_list = []
    #
    # for (id, link_def) in ast.link_ref_defs.items():
    #     if id.startswith("mnb-graphviz:"):
    #         # option
    #         continue
    #     dest, title = link_def
    #     if str((file_path.parent / dest).parent) == generated_dir:
    #         image_list.append(dest)


# print_spec_json(s)