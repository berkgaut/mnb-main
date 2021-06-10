from mnb import *

def build_plan(p: Plan):
    p.require_api(1,0)
    p.build_image("bberkgaut/mnb:%s" % MNB_VERSION, context_path=".")

    # plantuml_dir = Path("containers/plantuml")
    # plantuml_version = (plantuml_dir / "VERSION").read_text().strip()
    # plantuml_image = p.build_image("bberkgaut/mnb-plantuml:%s" % plantuml_version, context_path=plantuml_dir)

    dot2png(p, Path("docs/values-and-actions.dot"), dstsubdir="generated")
    dot2png(p, Path("docs/plan-generation.dot"), dstsubdir="generated")

    md2html(p, "README.md", dstsubdir="generated")
    md2pdf(p, "README.md", dstsubdir="generated")

def graphviz_image(p):
    graphviz_dir = Path("containers/graphviz")
    graphviz_version = (graphviz_dir / "VERSION").read_text().strip()
    return p.build_image("bberkgaut/graphviz:%s" % graphviz_version, context_path=graphviz_dir)

def dot2png(p: Plan, source: [str, PurePosixPath], dstsubdir=None):
    src_file, dst_file = src_dst(p, source, ".png", dstsubdir=dstsubdir)
    return p.exec(image=graphviz_image(p),
           command=["dot", "-Tpng",
                    "-o", dst_file,
                    src_file])