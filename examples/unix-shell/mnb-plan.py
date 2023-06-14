from spec import *

from spec_json import print_spec_json

s = Spec(spec_version=(1,0))
file_1 = "file_1"
bash_image = "bash"
s.pull_image(bash_image)
cmd1 = s.exec(bash_image, command=["bash", "-c", "echo '-*- Hallo -*-'"])
cmd1.output(file_1, through_stdout=True)
cmd2 = s.exec(bash_image, command=["bash", "-c", '>&2 echo "X=${X}"; echo "Hello stdout!"'])
from_stderr = "from_stderr"
from_stdout = "from_stdout"
cmd2.input(file=file_1, through_env='X')
cmd2.output(file=from_stderr, through_stderr=True)
cmd2.output(file=from_stdout, through_stdout=True)

print_spec_json(s)