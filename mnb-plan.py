import os
from mnb import *
from mnb.builder import Plan


def build_plan(p: Plan):
    print("build_plan")
    # p.build_image("bberkgaut/mnb:%s" % MNB_VERSION, ".")
    # p.build_image("bberkgaut/mnb-plantuml:0.0.1", "containers/plantuml")
    # # ignore_dirs, visitor, context = None):
    # def plan_for_file(p, _context, filepath : Path):
    #     suffix = filepath.suffix
    #     if suffix==".md":
    #         md2html(p, filepath)
    #     elif suffix in [".mindmap", ".plantuml", ".er"]:
    #         plantuml2png(p, filepath)
    #
    # walk_files(p, ".", DEFAULT_IGNORE_DIRS, plan_for_file)
    # d1=p.dst_file("sample.dat", through_stdout=True)
    # p.transform([], [d1], p.registry_image("bash"), ["bash", "-c", "echo '-*- Hallo -*-'"])
    # s1 = p.src_file("sample.dat", through_stdin=True)
    # s1a = p.src_file("sample.dat", through_env='SAMPLE_DAT')
    # s2 = p.src_file("notes.md")
    # d2 = p.dst_file("out", through_stdout=True)
    # p.transform([s1, s1a, s2], [d2], p.registry_image("bash"),
    #             ["bash", "-c", 'read X; sleep 1; >&2 echo "X=${X}"; echo Hello stdout ${SAMPLE_DAT}'])
    # return p
    p.require_api(1,0)
    p.image("bberkgaut/mnb:%s" % MNB_VERSION).from_context(".")

    plantuml_dir = Path("containers/plantuml")
    plantuml_version = (plantuml_dir / "version").read_text().strip()
    plantuml_image = p.image("bberkgaut/mnb-plantuml:%s" % plantuml_version).from_context(plantuml_dir)

    sample_txt = p.file("sample.txt")
    bash_image = p.image('bash').from_registry()
    p.exec(bash_image,
           ["bash", "-c", "echo '-*- Hallo -*-'"],
           outputs=[sample_txt.through_stdout()])
    p.exec(bash_image,
           ["bash", "-c", 'read X; sleep 1; >&2 echo "X=${X}"; echo Hello stdout ${SAMPLE_DAT}'],
           inputs=[sample_txt.through_stdin(), sample_txt.through_env("SAMPLE_DAT")],
           outputs=[p.file("stdout").through_stdout(), p.file("stderr").through_stderr()])
