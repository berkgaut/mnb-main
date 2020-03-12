import os
from mnb import *

IMAGE_VERSION="0.1"

def build_plan(p):
    p.build_image("bberkgaut/mnb:%s" % IMAGE_VERSION, ".")
    for (dir, dirs, filenames) in os.walk("."):
        dirpath = Path(dir)
        if ignore(dirpath):
            continue
        for filename in filenames:
            filepath = dirpath / filename
            purepath = str(PurePosixPath(filepath))
            suffix = filepath.suffix
            if suffix==".md":
                md2html(p, purepath)
            elif suffix in [".mindmap", ".plantuml", ".er"]:
                plantuml2png(p, purepath)
    d1=p.dst_file("sample.dat", through_stdout=True)
    p.transform([], [d1], p.registry_image("bash"), ["bash", "-c", "echo '-*- Hallo -*-'"])
    s1 = p.src_file("sample.dat", through_stdin=True)
    s1a = p.src_file("sample.dat", through_env='SAMPLE_DAT')
    s2 = p.src_file("notes.md")
    d2 = p.dst_file("out", through_stdout=True)
    p.transform([s1, s1a, s2], [d2], p.registry_image("bash"),
                ["bash", "-c", 'read X; sleep 1; >&2 echo "X=${X}"; echo Hello stdout ${SAMPLE_DAT}'])
    return p

def ignore(dirpath):
    for ignore in [".mnb.d", ".git", "__pycache__"]:
        if ignore in dirpath.parts:
            return True
    return False


if __name__=="__main__":
    main(build_plan)