from pathlib import Path, PurePosixPath

def src_dst(p, source, dstsuffix):
    src_path = PurePosixPath(source)
    src_file = p.src_file(source, through_file=src_path.name)
    dst_path = src_path.with_suffix(dstsuffix)
    dst_file = p.dst_file(str(dst_path), through_file=dst_path.name)
    return (src_file, dst_file)

def md2html(p, source, extra=[]):
    pandoc_image   = p.registry_image("dalibo/pandocker")
    src_file, dst_file = src_dst(p, source, ".html")
    extras_deps = [p.src_file(f, through_file=Path(f).name) for f in extra]
    p.transform(sources=extras_deps + [src_file],
                targets=[dst_file],
                image=pandoc_image,
                command=["-f", "markdown",
                          "-t", "html5",
                          "--standalone",
                          "-o", dst_file.workpath(),
                          src_file.workpath()])

def md2pdf(p, source):
    pandoc_image   = p.registry_image("dalibo/pandocker")
    src_file, dst_file = src_dst(p, source, ".pdf")
    p.transform(sources=[src_file],
                targets=[dst_file],
                image=pandoc_image,
                command=["-f", "markdown",
                          "-t", "latex",
                          "--pdf-engine=xelatex",
                          "-V", "mainfont=Liberation Sans",
                          "-V", "monofont=Liberation Mono",
                          "--standalone",
                          "-o", dst_file.workpath(),
                          src_file.workpath()])

def plantuml2png(p, source):
    plantuml_image = p.build_image("mnb/plantuml:1.2019.11", "containers/plantuml")
    src_file, dst_file = src_dst(p, source, ".png")
    p.transform(sources=[src_file],
                targets=[dst_file],
                image=plantuml_image,
                command=["-v", "-o", dst_file.workdir(), "-tpng",  src_file.workpath()])
