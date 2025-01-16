from spec import *
from mnb_version import MNB_VERSION_STR

with Spec(spec_version=(1, 0), description="build mnb images") as s:

    s.build_image(f"bberkgaut/mnb-spec-python:{MNB_VERSION_STR}",
                  extra_tags=["bberkgaut/mnb-spec-python:latest"],
                  context_path=".",
                  dockerfile_path="src/mnb-spec/Dockerfile")

    s.build_image(f"bberkgaut/mnb:{MNB_VERSION_STR}",
                  extra_tags=["bberkgaut/mnb:latest"],
                  context_path=".",
                  dockerfile_path="src/mnb-core/Dockerfile")

