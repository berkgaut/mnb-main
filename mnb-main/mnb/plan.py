import io
import shutil
import threading
from pathlib import Path, PurePosixPath

from docker.types import Mount

from mnb.log import *

MNB_RUN_PATH = PurePosixPath("/mnb/run")


class RegistryImage(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "registry_image(%s)" % self.name

    def prepare(self, client, state):
        if len(client.images.list(self.name)) == 0:
            low_level_api = client.api
            e = self.name.split(":")
            repo = e[0]
            if len(e) == 1:
                tag = "latest"
            else:
                tag = e[1]
            INFO("Pulling " + self.name)
            for line in low_level_api.pull(repo, tag=tag, stream=True, decode=True):
                INFO(line)
        else:
            INFO(self.name + " already pulled")


class BuildImage(object):
    def __init__(self, absrootpath, name, path):
        self.absrootpath = absrootpath
        self.name = name
        self.path = path

    def __str__(self):
        return "build_image(%s, %s)" % (self.name, self.path)

    def prepare(self, client, state):
        if len(client.images.list(self.name)) > 0:
            # TODO: implement smart rebuilt when dockerfile is modified
            INFO(self.name + " already built")
            return
        else:
            INFO("Building " + self.name)
            (image, logs) = client.images.build(path=self.path,
                                                tag=self.name,
                                                rm=False)
            for line in logs:
                INFO(line)


class SrcFile(object):
    def __init__(self, workfile, through_file, through_stdin, through_env, preprocessor):
        self.workfile = workfile
        self.through_file = through_file
        self.through_stdin = through_stdin
        self.through_env = through_env
        self.preprocessor = preprocessor

    def __str__(self):
        return "source(%s)" % self.workfile

    def workpath(self):
        """Mounted path"""
        return str(MNB_RUN_PATH / self.through_file)

    def workdir(self):
        return str(MNB_RUN_PATH)

    def prepare_source(self, workdir_path):
        # TODO: optimize the case without preprocessor through direct mount
        result_path = workdir_path / self.through_file
        with Path(self.workfile.internal_path).open('rb') as f:
            b = f.read()
            # TODO preprocess
            with Path(result_path).open('wb') as g:
                g.write(b)


class DstFile(object):
    def __init__(self, workfile, through_file, through_stdout):
        self.workfile = workfile
        self.through_file = through_file
        self.through_stdout = through_stdout

    def __str__(self):
        return "target(%s)" % self.workfile

    def workpath(self):
        return str(self._workpath())

    def _workpath(self):
        return PurePosixPath("/mnb/out") / self.through_file

    def workdir(self):
        return str(self._workpath().parent)

    def update_content(self, b):
        with Path(self.workfile.internal_path).open('wb') as f:
            f.write(b.encode('utf-8'))

    def update_file(self, outdir_path):
        with Path(outdir_path / self.through_file).open("rb") as i:
            b = i.read()
            with Path(self.workfile.internal_path).open('wb') as f:
                f.write(b)


class Transform(object):
    def __init__(self, absrootpath, sources, targets, image, command, entrypoint):
        self.absrootpath = absrootpath
        self.sources = sources
        self.targets = targets
        self.image = image
        self.command = command
        self.entrypoint = entrypoint
        for source in sources:
            source.workfile.add_outgoing_dependency(self)
        for target in targets:
            target.workfile.add_incoming_dependency(self)

    def __str__(self):
        r = str(self.image) + ": " + ", ".join([str(source) for source in self.sources]) + \
            " -> " + \
            ", ".join([str(target) for target in self.targets])
        return r

    def need_update(self, state):
        import datetime
        if len(self.targets) == 0:
            return True  # not entirely sure about this
        max_source_mtime = 0
        for source in self.sources:
            source_path = Path(source.workfile.internal_path)
            if not source_path.exists():
                continue  # TODO: or maybe fail?
            max_source_mtime = max(max_source_mtime, source_path.stat().st_mtime)
        min_target_mtime = datetime.datetime.now().timestamp()
        for target in self.targets:
            target_path = Path(target.workfile.internal_path)
            if not target_path.exists():
                return True
            min_target_mtime = min(min_target_mtime, target_path.stat().st_mtime)
        return max_source_mtime > min_target_mtime

    def clean(self):
        for target in self.targets:
            target_path = Path(target.workfile.internal_path)
            if target_path.exists():
                target_path.unlink()

    def run(self, client, state):
        ensure_writable_dir(Path(".mnb.d"))
        with Path(".mnb.d") / str(id(self)) as context_dir:
            context_path = Path(context_dir)
            ensure_writable_dir(context_path)
            workdir = ensure_writable_dir(context_path / "run")
            outdir = ensure_writable_dir(context_path / "out")
            mounts = []
            stdin_sources = []
            env = {}
            for source in self.sources:
                if source.through_file:
                    source.prepare_source(workdir)
                    m = Mount(source=str(self.absrootpath / source.workfile.internal_path),
                              target=str(source.workpath()),
                              type='bind',
                              read_only=True)
                    mounts.append(m)
                elif source.through_stdin:
                    stdin_sources.append(source)
                elif source.through_env:
                    with Path(source.workfile.internal_path).open("rb") as f:
                        v = f.read()
                        env[source.through_env] = v
            mounts.append(Mount(source=str(self.absrootpath / outdir),
                                target="/mnb/out/",
                                type="bind",
                                read_only=False))
            INFO("command: %s" % self.command)
            INFO("environment: %s" % env)
            container = client.containers.create(
                self.image.name,
                self.command,
                entrypoint=self.entrypoint,
                environment=env,
                mounts=mounts,
                detach=True,
                stdin_open=True)
            docker_socket = container.attach_socket(params=dict(interactive=True,
                                                                stdout=True,
                                                                stderr=True,
                                                                stdin=True,
                                                                stream=True,
                                                                demux=True))
            container.start()
            if len(stdin_sources) > 0:
                INFO("stdin sources: %s" % stdin_sources)
                stdin_stream = Path(stdin_sources[0].workfile.internal_path).open("rb")
            else:
                stdin_stream = io.BytesIO(b"")

            stdout_stream = io.BytesIO()
            stderr_stream = io.BytesIO()

            sender_thread = threading.Thread(target=sender, args=(docker_socket._sock, stdin_stream))
            receiver_thread = threading.Thread(target=receiver,
                                               args=(docker_socket._sock, stdout_stream, stderr_stream))
            sender_thread.start()
            receiver_thread.start()
            sender_thread.join()
            receiver_thread.join()
            for target in self.targets:
                if target.through_stdout:
                    target.update_content(stdout_stream.getvalue().decode("utf-8"))
                elif target.through_file:
                    target.update_file(outdir)
                # TODO: stderr out
            container.reload()
            #INFO("Status: %s" % container.attrs['State']['Status'])
            exit_code = container.attrs['State']['ExitCode']
            if exit_code == 0:
                # purge context dir if success
                shutil.rmtree(str(context_dir))
            else:
                # TODO: instead of stopping, we can mark outgoing dependencies as stalled
                #  and continue the rest of DAG. Not sure, how useful would be such behaviour
                raise Exception("Exit code: %s, context dir %s" % (exit_code, context_dir))
            container.stop()
            container.remove()


def receiver(sock, stdout_stream, stderr_stream):
    from docker.utils.socket import next_frame_header
    from docker.utils.socket import read_exactly
    while True:
        stream, length = next_frame_header(sock)
        if stream == -1:
            break
        received = read_exactly(sock, length)
        if stream == 1:
            stdout_stream.write(received)
        else:
            INFO("stderr: %s" % received.decode('utf-8'))
            stderr_stream.write(received)


def sender(sock, stdin_stream):
    n = 3
    buffer = b""
    while True:
        if len(buffer) == 0:
            buffer = stdin_stream.read(n)
            if len(buffer) == 0:
                break
        sent = sock.send(buffer)
        buffer = buffer[sent:]


def ensure_writable_dir(path):
    if path.exists() and not path.is_dir():
        raise Exception("Not a directory: %s" % path)
    path.mkdir(exist_ok=True)
    return path


class WorkFile:
    """A file that is part of execution plan"""

    def __init__(self, internal_path):
        # the path of file as seen mounted inside container
        self.internal_path = internal_path

        self.incoming_dependencies = set()
        self.outgoing_dependencies = set()

    def __str__(self):
        # return "%s\nincoming: %s\noutgoing: %s" % (self.internal_path, self.incoming_dependencies, self.outgoing_dependencies)
        return str(self.internal_path)

    def add_outgoing_dependency(self, d):
        self.outgoing_dependencies.add(d)

    def add_incoming_dependency(self, d):
        self.incoming_dependencies.add(d)


class Plan:
    def __init__(self, absroot_path):
        # Path of root on the host machine
        self.absroot_path = absroot_path

        self.transforms = []
        self.images = {}
        self.workfiles = {}

    def show(self):
        print("**** Images:\n")
        for image in self.images.values():
            print(image)
        print("**** Workpaths:\n")
        for wf in self.workfiles.values():
            print(wf)
        print("**** Transforms:\n")
        for t in self.runlist():
            print(t)

    def update(self, client, state):
        for image in self.images.values():
            image.prepare(client, state)
        for transform in self.runlist():
            if transform.need_update(state):
                transform.run(client, state)

    def clean(self):
        for transform in self.transforms:
            transform.clean()

    def src_file(self, src_path, through_file=None, through_stdin=None, through_env=None, preprocessor=None):
        wf = self.workfile_for_path(src_path)
        return SrcFile(wf, through_file, through_stdin, through_env, preprocessor)

    def dst_file(self, dst_path, through_file=None, through_stdout=None):
        wf = self.workfile_for_path(dst_path)
        return DstFile(wf, through_file, through_stdout)

    def workfile_for_path(self, file):
        # Transform work file path to some canonical form
        posix_path = PurePosixPath(file)
        if posix_path.is_absolute():
            # TODO: what should we do with absolute workpath here?
            raise Exception("Absolute work path not allowed: %s" % posix_path)
        if posix_path not in self.workfiles:
            wf = WorkFile(posix_path)
            self.workfiles[posix_path] = wf
            return wf
        else:
            return self.workfiles[posix_path]

    def transform(self, sources, targets, image, command, entrypoint=None):
        new_transform = Transform(self.absroot_path, sources, targets, image, command, entrypoint)
        self.transforms.append(new_transform)
        return new_transform

    # IDEA: intoduce runnable actions (transforms or image prepararion steps), depending on workfiles
    # In this case docker buidls would get integrated with file transformations => generated Dockerfiles
    def build_image(self, name, path):
        if name in self.images:
            # TODO: check conflict
            return self.images[name]
        else:
            img = BuildImage(self.absroot_path, name, path)
            self.images[name] = img
            return img

    def registry_image(self, name):
        if name in self.images:
            # TODO: check conflict
            return self.images[name]
        else:
            img = RegistryImage(name)
            self.images[name] = img
            return img

    def runlist(self):
        """
        Return topologically sorted list of transforms
        """
        # set of nodes without incoming edges
        s = set()
        # dependency graph representation optimizaed for toposort
        o = {}  # node -> outgoing connections (set of nodes depending on node)
        i = {}  # node -> incoming edges (set of nodes the node depends upon)
        # resulting list
        l = []
        # Here we execute two "nanopasses" (a term borrowed from compiler implementation)
        #
        # Firstly, we traverse a virtual full dependency graph (consisting of actions and data nodes)
        # and reduce it to dependency graph consiting of actions only (throwing away details about specific data nodes
        # causing action dependency).
        #
        # Secondly, we perform a toposort over actions
        #
        # Q: Maybe reuse https://github.com/pombredanne/bitbucket.org-ericvsmith-toposort

        # 1. Transform execution plan into dependency graph
        for transform in self.transforms:
            # if none of sources is a target of some other transform, add this node it to s
            if sum([len(source.workfile.incoming_dependencies) for source in transform.sources]) == 0:
                s.add(transform)
            # add outgoing edges to graph, if any
            for target in transform.targets:
                for depending_transform in target.workfile.outgoing_dependencies:
                    # add an edge transform -> depending_transform to the graph
                    if transform not in o:
                        o[transform] = set()
                    if depending_transform not in i:
                        i[depending_transform] = set()
                    o[transform].add(depending_transform)
                    i[depending_transform].add(transform)

        # 2. Now run Kahns algorithm (could be separated from previous to improve abstraction)
        while len(s) > 0:
            n = s.pop()
            l.append(n)
            if n in o:
                o_n = o[n]
                del o[n]
            else:
                o_n = set()
            while len(o_n) > 0:
                # remove edge from the graph
                m = o_n.pop()
                i[m].remove(n)
                if len(i[m]) == 0:
                    del i[m]
                    s.add(m)

        if len(o) != 0 or len(i) != 0:
            for (node, edges) in o.items():
                print("Source: " + str(node))
                for e in edges:
                    print("  Edge: " + str(e))
            raise Exception("Dependency graph has at least one cycle")
        else:
            return l


class State:
    pass
