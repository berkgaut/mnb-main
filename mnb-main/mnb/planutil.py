from pathlib import Path, PurePosixPath

from mnb.builder import Plan

def pandoc_image(p: Plan):
    return p.pull_image("dalibo/pandocker")

def plantuml_image(p: Plan):
    return p.pull_image("bberkgaut/mnb-plantuml")

def jq_image(p: Plan):
    return p.pull_image("imega/jq")

def mysql_client_image(p: Plan):
    return p.pull_image("imega/mysql-client")

def src_dst(p: Plan, source: [str, PurePosixPath], dstsuffix: str, dstsubdir = None):
    src_path = PurePosixPath(source)
    src_file = p.file(src_path).as_input(src_path.name)
    dst_name = PurePosixPath(src_path.name).with_suffix(dstsuffix)
    if dstsubdir is None:
        dst_parent = src_path.parent
    else:
        dst_parent = src_path.parent / dstsubdir
    dst_path = dst_parent / dst_name
    dst_file = p.file(dst_path).as_output(dst_path.name)
    return (src_file, dst_file)

def md2html(p: Plan, source: [str, PurePosixPath], extra=None, dstsubdir=None):
    if extra is None:
        extra = []
    src_file, dst_file = src_dst(p, source, ".html", dstsubdir=dstsubdir)
    extras_deps = [p.file(f).as_input(PurePosixPath(f).name) for f in extra]
    return p.exec(image=pandoc_image(p),
           command=["-f", "markdown",
                    "-t", "html5",
                    "--standalone",
                    "-o", dst_file,
                    src_file],
           inputs=extras_deps)

def md2pdf(p: Plan, source, dstsubdir=None):
    src_file, dst_file = src_dst(p, source, ".pdf", dstsubdir=dstsubdir)
    p.exec(image=pandoc_image(p),
           command=["-f", "markdown",
                    "-t", "latex",
                    "--pdf-engine=xelatex",
                    "-V", "mainfont=Liberation Sans",
                    "-V", "monofont=Liberation Mono",
                    "--standalone",
                    "-o", dst_file,
                    src_file])

def plantuml2png(p, source, dstsubdir=None):
    src_file, dst_file = src_dst(p, source, ".png", dstsubdir=dstsubdir)
    p.transform(sources=[src_file],
                targets=[dst_file],
                image=plantuml_image(p),
                command=["-v", "-o", dst_file, "-tpng",  src_file])

def plantuml2pdf(p, source, dstsubdir=None):
    src_file, dst_file = src_dst(p, source, ".pdf", dstsubdir=dstsubdir)
    p.transform(sources=[src_file],
                targets=[dst_file],
                image=plantuml_image(p),
                command=["-v", "-o", dst_file, "-tpdf",  src_file])

DEFAULT_IGNORE_DIRS = [".mnb.d", ".git", "__pycache__"]

def walk_files(p, dir, ignore_dirs, visitor, context = None):
    def walk_files_1(dir_path : Path):
        if not dir_path.is_dir():
            raise Exception("%s is not a directory" % dir_path)
        for path in dir_path.iterdir():
            if path.is_dir() and not path.name in ignore_dirs:
                walk_files_1(path)
            elif path.is_file():
                visitor(p, context, path)
    walk_files_1(Path(dir))

