from spec import *
from mnb_version import MNB_VERSION_STR

from spec_json import print_spec_json

s = Spec(spec_version=(1,0))
s.build_image("mnb" + ":" + MNB_VERSION_STR, context_path=".", dockerfile_path="src/Dockerfile")
s.build_image("mnb-python-spec" + ":" + MNB_VERSION_STR, context_path=".", dockerfile_path="containers/mnb-spec-python/Dockerfile")

print_spec_json(s)
