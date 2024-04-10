from spec import *

from spec_json import print_spec_json

s = Spec(spec_version=(1,0))
file_1 = "examples/unix-shell/mnb-generated/file.txt"
bash_image = "bash:5.2"
s.pull_image(bash_image)

cmd1 = s.exec(bash_image, command=["bash", "-c", "echo '-*- Hallo -*-'"])
cmd1.output(file_1, through_stdout=True)

cmd2 = s.exec(bash_image, command=["bash", "-c", '>&2 echo "X=${X}"; echo "Hello stdout!"'])
cmd2.input(file=file_1, through_env='X') #FIXME: this does not work as expected
cmd2.output(file="examples/unix-shell/mnb-generated/stderr.txt", through_stderr=True)
cmd2.output(file="examples/unix-shell/mnb-generated/stdout.txt", through_stdout=True)

print_spec_json(s)