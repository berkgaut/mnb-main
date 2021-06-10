# Mnb -- Container-based Executable Notes

## What is `mnb`?

`mnb` is an utility to maintain a collection of notes, code snippets and visualizations.

You can think of it as a specialized form of `make` running inside a Docker container,
and launching other containers to perform actions.

The rationale is to lower the threshold for using some nice tools otherwise requiring careful installation and configuration
(think TeX, pandoc or graphviz).
With mnb the only requirements are Docker and a standard shell (bash or cmd.exe)  
 
`mnb` is a pet project, driven by my search for a rich medium for note-keeping.

## Quick Start

To create mnb startup script `mnb`

```bash
mkdir mnb-demo
cd mnb-demo
docker run -v $PWD:/mnb/run --rm bberkgaut/mnb:latest scripts
```

ask `mnb` to generate and execute a plan:

```bash
./mnb update
```

## Key Principles

__File-based__: code, datasets and notes are stored in individual files.
Which means, `mnb` plays nice with version control systems, text editors and other standard tools.

__Data-driven__: when you change some file, `mnb` would update all dependencies

__Container-based__: actions are performed by regular Docker containers. Any container reading input from files and writing output to a file could be an action. 

__Pure (as in function)__: every container has access only to specified input files. Every container execution only changes specified output files.

__Minimalistic & extensible__: `mnb` tracks dependencies and runs containers. Everything else comes as separate containers. 

__Self-contained__: `mnb` itself runs inside a container. All you need to run `mnb` is a standard shell and Docker installed.
All custom images are either pulled from a Docker registry or built by `mnb`.  

## Non-goals

`mnb` does not aim to solve image build fragility (when image build depends on potentially transient external artefacts)

`mnb` is not trying to be fast at the moment. It is not a "big data" tool. Large datasets would be slow

`mnb` is not a container orchestration tool

`mnb` is not an alternative to `docker-compose`. The latter composes long-running systems out of networked containers,
while mnb composes systems out of unix processes reading and writing files   

`mnb` is just as secure as plain `docker run ...` command

## Use-cases

What `mnb` could be useful for:

* Executable notes: keeping notes together with some code
* Getting organized: keeping TODO lists and calendars (e.g. org-mode style) along with reporting, formatting etc 
* Data, code and prose in a unified flow: reproducible research, data journalism
* Software documentation and verification

## Execution Plan and Actions

![Values and Actions](docs/generated/values-and-actions.png)

`mnb` works according to a plan - a list of actions to perform on values.

Values are either images or files.

There are following types of actions:

- Pull an image from registry
- Build an image from some directory (called a build context)
- Run a container, passing some files as inputs and fetching some files as outputs

When running a container, it's also possible to pass inputs through environment variables and stdin, and fetch results from stdout or stderr. 

Each value (file or image) could be *produced* by at most one action, and *consumed* by any number of actions.
Actions are executed in such order that producers are always executed before consumers.

## Plan Generation

Execution plans do not have any templating capabilities like Makefiles.
Instead, `mnb` plan consists of very fine-grained actions consuming and producing specific files.
Plans are not intended to be written by hands. Instead, they are generated by programs in general-purpose programming languages.

At the moment, plans are generated by `mnb` itself using a DSL embedded in Python (see [Python DSL for Plans](docs/python-dsl.md)).
In future, it would be possible to run an arbitrary container to emit a plan.

![Plan Generation](docs/generated/plan-generation.png)

## Further Reading

* [Examples](examples/)
* [Python DSL for Plans](docs/python-dsl.md)
* TBD: JSON Representation for Plans


