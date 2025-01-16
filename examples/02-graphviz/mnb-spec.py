from spec import *
import sys

# If you want some output from the script, you can use stderr, as stdout is expected to contain JSON
print("Hello from Python script which uses eDSL to generate mnb spec!", file=sys.stderr)

with Spec(spec_version=(1, 0), description="python-base example") as s:
    mnb_generated = PurePosixPath("mnb-generated")

    # Build GraphViz image
    # In this example, the build context is pulled from a git repo
    graphviz_image = s.build_image(
        "trivial-graphviz",
        context_path="containers/graphviz",
        from_git=FromGit(repo="https://github.com/berkgaut/mnb-main.git", rev="master"))

    def dot2png(source: StringOrPath, output: StringOrPath) -> None:
        source_path = to_path(source)
        output_path = to_path(output)
        s.exec(graphviz_image,
               inputs=[Input(value=File(source_path), through=ThroughFile(source_path.name))],
               outputs=[Output(value=File(output_path), through=ThroughFile(output_path.name))],
               command=["dot", "-Tpng", "-o", output_path.name, source_path.name])

    dot2png("example.dot", mnb_generated / "example.png")
