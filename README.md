# Mnb -- a Multy-Kernel Container-Based Notebook

```
$ mkdir mnb-demo && cd mnb-demo 

$ docker run bberkgaut/mnb run-demo

Welcome to mnb

Web-interface is served on: http://localhost?token=R0Z6noIoiBLdY2N5Lg

# web interface provides update and sizes commands
```

## What is mnb?

`mnb` is a simple utility to maintain notebooks -- documents which contain executable code snippets intertwined with visualizations and prose. `mnb` was born as (and still is) a pet project and driven mostly by search of a suitable medium for lifelong note-keeping. Its roots are within a range of interactive computation systems, both modern (Jupyter and friends) and classic (Smalltalk, Plan9 Acme).

## Design Choices

`mnb` is:

* File-based: code, datasets and notes are stored in individual files
* Data-driven: computations are performed on-demand when data, code or configuration changes
* Container-based: interpreters are Docker containers, and any container could be an interpreter
* Minimalist and modular: `mnb` is to track dependencies and run containers, everything else comes as separate containers managed by `mnb`

## Design Implications

* Being file-based makes `mnb` friendly to version control systems, code editors and other file-based tools
* Thanks to Docker, the complexity of tool instalation and configuration is hidden; even rare and/or hard to configure tools could be easily tried and adopted
* Being data-driven (goal-directed) and file-based makes `mnb` a special case of build system
* Every running container only has access to explicitly specified set of input files, and only explicitly specified output files are available for further consumers (this approach resembles Bazel)
* In particular, knowing all dependencies could help offloading containers to remote machines or paralellize execution (something I have not tried yet)
* Being a special-purpose build system, `mnb` can maintain custom Docker images, with Dockerfiles being parts of a notebook. This simplifies experimentation and customization of Docker images
* Main `mnb` utility runs inside a container. All you need to run `mnb` is a standard shell  and Docker
* Which means, `mnb` runs on Windows, thanks to Docker for Windows

## Some Use-cases

Some ideas of what could be done with `mnb`:

* Tasks typically done with notebooks: reproducible data science, ad hoc data extraction and analysis
* Note-taking and journaling: keeping notes together with formatting and publishing scripts
* Keeping TODO lists and calendars (org-mode style) along with some automation
* Software documentation/verification projects
