from mnb import *

def build_plan(p: Plan):
    p.require_api(1,0)

    sample_txt = p.file("sample.txt")
    bash_image = p.pull_image('bash')
    p.exec(bash_image,
           ["bash", "-c", "echo '-*- Hallo -*-'"],
           outputs=[sample_txt.through_stdout()])
    p.exec(bash_image,
           ["bash", "-c", 'read X; sleep 1; >&2 echo "X=${X}"; echo Hello stdout ${SAMPLE_DAT}'],
           inputs=[sample_txt.through_stdin(),
                   sample_txt.through_env("SAMPLE_DAT")],
           outputs=[p.file("stdout").through_stdout(),
                    p.file("stderr").through_stderr()])
