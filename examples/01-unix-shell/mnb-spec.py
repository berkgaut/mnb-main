# In principle, any program producing JSON output can be used to generate mnb specifications
# This file uses simple DSL embedded in Python to generate a build specification

from spec import *
from pathlib import PurePosixPath

with Spec(spec_version=(1, 0), description="Run some regular shell commands") as s:

    # a directory to keep intermediate files
    mnb_generated = PurePosixPath("mnb-generated")

    # pull stock bash image
    bash_image = s.pull_image("bash:5.2")

    my_file = mnb_generated / "my_file.txt"

    # execute bash command and redirect output to the file
    s.exec(
        bash_image,
        command=["bash", "-c", "echo '-*- Hallo -*-'"]
    ).output(
        my_file,
        through_stdout=True
    )

    # More complex example
    # - the content of file my_file would be passed to the command through environment variable X
    # - composite command would write to stdout and stderr
    # - stdout would be redirected to file stdout.txt
    # - stderr would be redirected to file stderr.txt
    #
    # Since output of previous command is used as input to this command,
    # this command deemed dependent on the previous command and would be executed after it
    s.exec(
        bash_image,
        command=["bash", "-c", '>&2 echo "X=${X}"; echo "Hello stdout!"']
    ).input(
        file=my_file,
        through_env='X'
    ).output(
        file=mnb_generated / "stderr.txt",
        through_stderr=True
    ).output(
        file=mnb_generated / "stdout.txt",
        through_stdout=True
    )
    # NOTE: on exit from Spec context, a JSON specification would be printed to stdout
