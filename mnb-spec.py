from spec import *
from spec_json import print_spec_json
from mnb_version import MNB_VERSION_STR

s = Spec(spec_version=(1, 0), description="build mnb images")

GRAPHVIZ="trivial-graphviz"

s.build_image(f"bberkgaut/mnb-spec-python:{MNB_VERSION_STR}",
              context_path=".",
              dockerfile_path="src/mnb-spec/Dockerfile")

s.build_image(f"bberkgaut/mnb:{MNB_VERSION_STR}",
              context_path=".",
              dockerfile_path="src/mnb-core/Dockerfile")

print_spec_json(s)
