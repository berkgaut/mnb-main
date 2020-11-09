import io
import shutil
import threading
from pathlib import Path, PurePosixPath
from typing import List

from docker.types import Mount

from mnb.log import *

MNB_RUN_PATH = PurePosixPath("/mnb/run")

class Context:
    """
    Context passed around during plan preparation and execution
    """
    def __init__(self, docker_client, state_storage):
        self.docker_client = docker_client
        self.state_storage = state_storage

    def close(self):
        self.docker_client.close()
        self.state_storage.close()


class Action(object):
    def prepare(self, context):
        raise NotImplementedError

    def need_update(self, context):
        raise NotImplementedError

    def run(self, context):
        raise NotImplementedError

    def clean(self, context):
        raise NotImplementedError

    def inputs(self):
        raise NotImplementedError

    def outputs(self):
        raise NotImplementedError


class PullImage(Action):
    def set_dependant_image(self, image):
        self.image = image
        self.name = image.name

    def __str__(self):
        return "registry_image(%s)" % self.name

    def inputs(self):
        return set()

    def outputs(self):
        return {self.image}

    def prepare(self, context):
        # TODO: move here code from planx to check RepoDigests
        if len(context.docker_client.images.list(self.name)) == 0:
            low_level_api = context.docker_client.api
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

    def need_update(self, context):
        return False

    def run(self, context):
        pass

    def clean(self, context):
        # TODO: clean image
        pass


class BuildImage(Action):
    def __init__(self, absrootpath, path, src_files = None):
        if not src_files:
            src_files = []
        self.absrootpath = absrootpath
        self.path = path
        self.sources = set(src_files)

    def inputs(self):
        return {source.workfile for source in self.sources}

    def outputs(self):
        return {self.image}

    def set_dependant_image(self, image):
        self.image = image
        self.name = image.name

    def __str__(self):
        return "build_image(%s, %s)" % (self.name, self.path)

    def prepare(self, context):
        pass

    def need_update(self, context):
        if len(context.docker_client.images.list(self.name)) > 0:
            # TODO: look at sources
            INFO(self.name + " already built")
            return False
        else:
            return True

    def run(self, context):
        INFO("Building " + self.name)
        # TODO: copy only sources to a new context
        (image, logs) = context.docker_client.images.build(path=self.path,
                                                           tag=self.name,
                                                           rm=False)
        for line in logs:
            INFO(line)

    def clean(self, context):
        # TODO: clean image
        pass


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
        """
        Returns a string representing path inside container
        Part of plan builder API
        """
        return str(MNB_RUN_PATH / self.through_file)

    def workdir(self):
        """
        Returns a string representing path to containing directory inside container
        Part of plan builder API
        """
        return str(MNB_RUN_PATH)


class DstFile(object):
    def __init__(self, workfile, through_file, through_stdout):
        self.workfile = workfile
        self.through_file = through_file
        self.through_stdout = through_stdout

    def __str__(self):
        return "target(%s)" % self.workfile

    def workpath(self):
        """
        Returns a string representing file inside container
        Part of plan builder API
        """
        return str(self._workpath())

    def _workpath(self):
        return PurePosixPath("/mnb/out") / self.through_file

    def workdir(self):
        """
        Returns a string representing file's containing directory inside container
        Part of plan builder api
        """
        return str(self._workpath().parent)


class Transform(Action):
    def __init__(self, absrootpath, sources, targets, image, command, entrypoint):
        self.absrootpath : Path = absrootpath
        self.sources: List[SrcFile] = sources
        self.targets: List[DstFile] = targets
        self.image = image
        self.command: List[str] = command
        self.entrypoint:str = entrypoint

    def inputs(self):
        result = {source.workfile for source in self.sources}
        result.add(self.image)
        return result

    def outputs(self):
        return {target.workfile for target in self.targets}

    def __str__(self):
        r = str(self.image) + ": " + ", ".join([str(source) for source in self.sources]) + \
            " -> " + \
            ", ".join([str(target) for target in self.targets])
        return r

    def prepare(self, context):
        pass

    def need_update(self, context):
        # mtime comparison considered harmful https://apenwarr.ca/log/20181113
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

    def clean(self, context):
        for target in self.targets:
            target_path = Path(target.workfile.internal_path)
            if target_path.exists():
                target_path.unlink()

    def run(self, context):
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
                    # TODO: optimize the case without preprocessor through direct mount
                    # copy source file into destination
                    result_path = workdir / source.through_file
                    with Path(source.workfile.internal_path).open('rb') as i:
                        bytes = i.read()
                        # TODO preprocess
                        with Path(result_path).open('wb') as o:
                            o.write(bytes)
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
            container = context.docker_client.containers.create(
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
                    with Path(target.workfile.internal_path).open('wb') as f:
                        f.write(stdout_stream.getvalue())
                elif target.through_file:
                    with Path(outdir / target.through_file).open("rb") as i:
                        bytes = i.read()
                        with Path(target.workfile.internal_path).open('wb') as o:
                            o.write(bytes)
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


class ValueBase:
    def __init__(self):
        self._producer = None
        self._consumers = set()

    def add_consumer(self, consumer):
        self._consumers.add(consumer)

    def set_producer(self, producer):
        self._producer = producer

    def producer(self):
        return self._producer

    def consumers(self):
        return self._consumers


class WorkFile(ValueBase):
    """A file that is a part of execution plan"""

    def __init__(self, internal_path):
        super().__init__()
        # the path of file as seen mounted inside container
        self.internal_path = internal_path

    def __str__(self):
        # return "%s\nincoming: %s\noutgoing: %s" % (self.internal_path, self.incoming_dependencies, self.outgoing_dependencies)
        return str(self.internal_path)


class Image(ValueBase):
    """An image that is a part of execution plan"""
    def __init__(self, name: str):
        super().__init__()
        self.name : str = name


class Plan:
    def __init__(self, absroot_path : str):
        # Path of root on the host machine
        self.absroot_path : str = absroot_path
        self.transforms = set()
        self.images_sources = set()
        self.workfiles = dict()
        self.images = dict()

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

    def update(self, context):
        runlist = self.runlist()
        for action in runlist:
            action.prepare(context)
        for action in runlist:
            if action.need_update(context):
                action.run(context)

    def clean(self, context):
        for action in self.runlist():
            action.clean(context)

    ### Builder
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
        self.transforms.add(new_transform)
        for source in sources:
            source.workfile.add_consumer(new_transform)
        for target in targets:
            # TODO: check conflict
            target.workfile.set_producer(new_transform)
        image.add_consumer(new_transform)
        return new_transform

    def build_image(self, name, path, src_files = None):
        if name in self.images:
            raise Exception("Image build %s already declared; reuse the value" % name)
        else:
            image_source = BuildImage(self.absroot_path, path, src_files)
            return self._new_image(name, image_source)

    def registry_image(self, name):
        if name in self.images:
            if not isinstance(self.images[name].producer(), PullImage):
                raise Exception("Conflict: image %s declared in different way" % name)
            return self.images[name]
        else:
            image_source = PullImage()
            return self._new_image(name, image_source)

    def _new_image(self, name, source):
        if name in self.images:
            raise Exception("conflict: image %s already declared" % name)
        image = Image(name)
        self.images[name] = image
        image.set_producer(source)
        source.set_dependant_image(image)
        self.images_sources.add(source)
        return image

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
        all_actions = self.transforms.union(self.images_sources)
        for action in all_actions:
            # if none of inputs is produced by some other action, add this action it to set s (nodes without incoming edges)
            if all(map(lambda input_value: input_value.producer() is None, action.inputs())):
                s.add(action)
            # add outgoing edges to graph, if any
            for output in action.outputs():
                for depending_action in output.consumers():
                    # add an edge action -> depending_action to the graph
                    if action not in o:
                        o[action] = set()
                    if depending_action not in i:
                        i[depending_action] = set()
                    o[action].add(depending_action)
                    i[depending_action].add(action)

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

