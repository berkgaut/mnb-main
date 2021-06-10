# Python-based Plan DSL

By default, `mnb` uses itself as a plan generator. In this case, it reads `mnb-plan.py` file
and calls `build_plan` function in it,
passing a plan API object as an argument.

`mnb-plan.py` file could look like

```python
from mnb import *

def build_plan(p: Plan):
    p.exec(image=p.pull_image(name="dalibo/pandocker"),
           command=["-f", "markdown",
                    "-t", "latex",
                    "--pdf-engine=xelatex",
                    "-V", "mainfont=Liberation Sans",
                    "-V", "monofont=Liberation Mono",
                    "--standalone",
                    "-o", p.file("README.pdf").as_output(),
                    p.file("README.md").as_input()])
``` 

`mnb` comes with a shorthand for pandoc action above:

```python
from mnb import *

def build_plan(p: Plan):
  md2pdf(p, "README.md")
```

There is also a utility to recursively walk directory tree:

```python
from mnb import *

def build_plan(p: Plan):
    def plan_for_file(p, _context, filepath : Path):
        suffix = filepath.suffix
        if suffix==".md":
            md2html(p, filepath)
        elif suffix in [".mindmap", ".plantuml", ".er"]:
            plantuml2png(p, filepath)
    walk_files(p, ".", DEFAULT_IGNORE_DIRS, plan_for_file)
    return p
```

**NOTE**: In future versions `walk_files` would support `.gitignore` files

Beside passing files to actions, it's possible to pass file content via stdin:

```python
    p.exec(image=p.pull_image(name="bash"), 
           command=["wc"],
           inputs=[p.file("data.csv").through_stdin()])
```

Command stdout could be captured into an output file as well:
```python
    p.exec(image=p.pull_image(name="bash"), 
           command=["echo", "'-*- Hello, world! -*-'"],
           outputs=[p.file("sample.txt").through_stdout()])
```

And there is a `.through_stderr()` to capture stderr.

It's also possible to pass file content as an environment varibale:

```python
    p.exec(image=p.pull_image(name="bash"),
           command=["echo", "${X}"],
           inputs=[p.file("sample.txt").through_env("X")])
```

