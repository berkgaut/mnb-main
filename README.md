# Mnb -- a Multy-Kernel Container-Based Notebook

```bash
mkdir mnb-demo
cd mnb-demo
docker run -v $PWD:/mnb/run --rm bberkgaut/mnb:latest scripts
```

## What is `mnb`?

`mnb` is an utility to maintain a collection of code snippets, visualizations and prose. `mnb` is a pet project, driven by search of a suitable medium for lifelong note-keeping.

I used to maintain my notes with make, but it has some known drawbacks. I also wanted to unlock the use of rare and non-standard tools through the use of Docker. That's why I wrote `mnb`.

## Design Principles

File-based: code, datasets and notes are stored in individual files. This means, `mnb` plays well with version control systems, editors and other tools.

Data-driven: when you change some file, `mnb` would update all dependencies.

Container-based: interpreters are regular Docker containers. Any container reading input from files and writing output to a file could be an interpreter. 

Pure: every container has access only to specified inputs. Every container only changes specified outputs.

Modular: `mnb` tracks dependencies and runs containers. Everything else comes as separate containers. 

Self-hosted: `Mnb` is a special-purpose build system. It helps maintain custom Docker images, with Dockerfiles being parts of a notebook. This simplifies experimentation and customization of Docker images.

Self-contained: `mnb` itself runs inside a container. All you need to run `mnb` is a standard shell and Docker installed 

## Windows Support

`mnb` runs on Windows, thanks to Docker for Windows

```text
C:\Users\berkg>mkdir mnb-demo
C:\Users\berkg>cd mnb-demo
C:\Users\berkg\mnb-demo>docker run -v %cd%:/mnb/run --rm bberkgaut/mnb:latest scripts
```

## Use-cases

What `mnb` could be useful for:

* Ad hoc data extraction and analysis
* Note-taking and journaling: keeping notes together with formatting and publishing scripts
* Keeping TODO lists and calendars (org-mode style) along with some automation
* Software documentation/verification projects

## Plan files

TBD