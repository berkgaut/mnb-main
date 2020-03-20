import os
from mnb import *

def build_plan(p):
    def plan_for_file(p, _context, filepath : Path):
        suffix = filepath.suffix
        if suffix==".md":
            md2html(p, filepath)
        elif suffix in [".mindmap", ".plantuml", ".er"]:
            plantuml2png(p, filepath)
    walk_files(p, ".", DEFAULT_IGNORE_DIRS, plan_for_file)
    return p

