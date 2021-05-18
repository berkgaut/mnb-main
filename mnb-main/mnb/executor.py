import io
import shutil
import threading
from pathlib import PurePosixPath, Path
from typing import Any, Set, Iterable, Dict

from mnb.builder import Image, Plan, WorkFile, Exec, InputFile, Stdin, InputFileThroughEnv, OutputStream, OutputFile
from mnb.log import *

VERSION_MAJOR = 1
VERSION_MINOR = 0


class Context(object):
    """
    Context passed around during plan execution
    """

    def __init__(self, docker_client, state_storage, abs_rootpath):
        self.docker_client = docker_client
        self.state_storage = state_storage
        self.abs_rootpath: Path = abs_rootpath

    def close(self):
        self.docker_client.close()
        self.state_storage.close()


class Action(object):
    """
    Action consumes and produces values
    """

    def run(self, context: Context):
        """Perform action"""
        raise NotImplementedError

    def inputs(self) -> set['ValueBase']:
        """Get list of input values"""
        raise NotImplementedError

    def outputs(self) -> set['ValueBase']:
        """Get list of output values"""
        raise NotImplementedError


class ValueBase(object):
    """
    Values are produced by one single action and could be consumed by any number of actions.

    Values could become obsolete (e.g. file gets changed or docker image gets updated).
    Missing value (file or image) is considered obsolete.
    Producers of obsolete values would be re-run before all consumers.
    """

    _consumers: set[Action] = set()
    _producer: Action = None

    def add_consumer(self, consumer: Action):
        self._consumers.add(consumer)

    def set_producer(self, producer: Action):
        self._producer = producer

    def producer(self) -> Action:
        return self._producer

    def consumers(self) -> set[Action]:
        return self._consumers

    def prepare(self, context):
        """
        Check if the value needs update
        """
        raise NotImplementedError

    def needs_update(self, context) -> bool:
        raise NotImplementedError


class ImageValue(ValueBase):
    _plan_element: Image

    def __init__(self, plan_element: Image):
        super().__init__()
        self._plan_element = plan_element

    def _name(self) -> str:
        return self._plan_element.name


class RegistryImageValue(ImageValue):
    _needs_update: bool

    def __init__(self, plan_element: Image):
        super().__init__(plan_element)
        self._needs_update = True

    def _get_local_repodigest(self, context):
        """
        Return RepoDigest of image at local Docker daemon
        """
        images_list = context.docker_client.images.list(self._name())
        if len(images_list) == 0:
            return None
        sorted_by_created = sorted(images_list, key=lambda x: x.attrs.get('Created'), reverse=True)
        image = sorted_by_created[0]
        repo_digests = image.attrs.get('RepoDigests')
        if len(repo_digests) != 1:
            raise Exception("Ambigous RepoDigests, do not know how to handle this: %s" % str(repo_digests))
        repo_digest = repo_digests[0]
        return repo_digest.split("@")[-1]

    def _get_registry_repodigest(self, context):
        """
        Returns RepoDigest of an image in a registry
        """
        registry_data = context.docker_client.images.get_registry_data(self._name())
        repo_digest = registry_data.attrs['Descriptor']['digest']
        return repo_digest

    def prepare(self, context):
        registry_repodigest = self._get_registry_repodigest(context)
        local_repodigest = self._get_local_repodigest(context)
        self._needs_update = (local_repodigest != registry_repodigest)

    def needs_update(self, context) -> bool:
        return self._needs_update


class FileValue(ValueBase):
    _plan_element: WorkFile

    def __init__(self, plan_element: WorkFile):
        super().__init__()
        self._plan_element = plan_element

    def prepare(self, context):
        pass

    def needs_update(self, context) -> bool:
        # TODO use state
        return True


class PullImageAction(Action):
    _plan_element: Image
    _image_value: RegistryImageValue

    def __init__(self, plan_element: Image):
        self._plan_element = plan_element

    def set_output_image(self, image_value: RegistryImageValue):
        self._image_value = image_value

    def inputs(self):
        return set()

    def outputs(self):
        return {self._image_value}

    def run(self, context):
        low_level_api = context.docker_client.api
        e = self._name().split(":")
        repo = e[0]
        if len(e) == 1:
            tag = "latest"
        else:
            tag = e[1]
        INFO("Pulling " + self._name())
        for line in low_level_api.pull(repo, tag=tag, stream=True, decode=True):
            INFO(line)

    def _name(self):
        return self._plan_element.name


class ImageToBuildValue(ImageValue):
    _needs_update: bool

    def __init__(self, plan_element: Image):
        super().__init__(plan_element)

    def prepare(self, context):
        images_list = context.docker_client.images.list(self._name())
        self._needs_update = (len(images_list) == 0)

    def needs_update(self, context) -> bool:
        return self._needs_update


class BuildImageAction(Action):
    _inputs: set[ValueBase] = set()
    _plan_element: Image
    _image_value: ImageToBuildValue = None

    def __init__(self, plan_element: Image):
        self._plan_element = plan_element

    def inputs(self) -> set[ValueBase]:
        return self._inputs

    def outputs(self):
        return {self._image_value}

    def set_output_image(self, image_value: ImageToBuildValue):
        self._image_value = image_value

    def run(self, context):
        INFO("Building " + self._plan_element.name)
        # TODO: create context copy, copy only sources to context
        (image, logs) = context.docker_client.images.build(path=str(self._plan_element.build_from_context),
                                                           tag=self._plan_element.name,
                                                           rm=False)
        for line in logs:
            INFO(line)

    def add_input(self, value: ValueBase):
        self._inputs.add(value)


class ExecAction(Action):
    _plan_fragment: Exec
    _image: ImageValue
    _inputs: set['ValueBase'] = set()
    _outputs: set['ValueBase'] = set()

    def __init__(self, plan_fragment: Exec, image: ImageValue):
        self._plan_fragment = plan_fragment
        self._image = image

    def run(self, context):
        from docker.types import Mount

        ensure_writable_dir(Path(".mnb.d"))
        with Path(".mnb.d") / str(id(self)) as context_path:
            ensure_writable_dir(context_path)
            workdir = ensure_writable_dir(context_path / "run")
            outdir = ensure_writable_dir(context_path / "out")
            mounts = []
            stdin_sources = []
            env = {}
            for source in self._plan_fragment.inputs:
                if isinstance(source, InputFile):
                    preprocess = False # TODO: add preprocessor spec
                    if (preprocess):
                        # copy source file into destination
                        result_path = workdir / source.through_path
                        with Path(source.workfile.posix_path).open('rb') as i:
                            bytes = i.read()
                            # TODO preprocess
                            with Path(result_path).open('wb') as o:
                                o.write(bytes)
                        m = Mount(source=str(context.abs_rootpath / result_path),
                                  target=str(PurePosixPath("/mnb/run") / source.through_path),
                                  type='bind',
                                  read_only=True)
                        mounts.append(m)
                    else:
                        m = Mount(source=str(context.abs_rootpath / source.workfile.posix_path),
                                  target=str(PurePosixPath("/mnb/run") / source.through_path),
                                  type='bind',
                                  read_only=True)
                        mounts.append(m)
                elif isinstance(source, Stdin):
                    stdin_sources.append(source)
                elif isinstance(source, InputFileThroughEnv):
                    with Path(source.workfile.posix_path).open("rb") as f:
                        v = f.read()
                        env[source.name] = v
            mounts.append(Mount(source=str(context.abs_rootpath / outdir),
                                target="/mnb/out/",
                                type="bind",
                                read_only=False))
            INFO("command: %s" % self._plan_fragment.command)
            INFO("environment: %s" % env)
            INFO("mounts: %s" % mounts)
            container = context.docker_client.containers.create(
                self._plan_fragment.image.name,
                self._plan_fragment.command,
                entrypoint=self._plan_fragment.entrypoint,
                environment=env,
                mounts=mounts,
                working_dir="/mnb/run",
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
                # TODO: concatenate multiple input streams
                stdin_stream = Path(stdin_sources[0].workfile.posix_path).open("rb")
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
            for target in self._plan_fragment.outputs:
                if isinstance(target, OutputStream):
                    with Path(target.workfile.posix_path).open('wb') as f:
                        if target.through_stdout:
                            f.write(stdout_stream.getvalue())
                        elif target.through_stderr:
                            f.write(stderr_stream.getvalue())
                if isinstance(target, OutputFile):
                    with Path(outdir / target.through_path).open("rb") as i:
                        bytes = i.read()
                        with Path(target.workfile.posix_path).open('wb') as o:
                            o.write(bytes)
            container.reload() # update container status
            INFO("Status: %s" % container.attrs['State']['Status'])
            exit_code = container.attrs['State']['ExitCode']
            if exit_code == 0:
                # when success, purge context dir
                shutil.rmtree(str(context_path))
            else:
                # TODO: instead of stopping, we can mark outgoing dependencies as stalled
                #  and continue the rest of DAG. Not sure, how useful would be such behaviour
                raise Exception("Exit code: %s, context dir %s" % (exit_code, context_path))
            container.stop()
            container.remove()

    def inputs(self) -> set['ValueBase']:
        result = self._inputs.copy()
        result.add(self._image)
        return result

    def outputs(self) -> set['ValueBase']:
        return self._outputs

    def add_input(self, input: ValueBase):
        self._inputs.add(input)

    def add_output(self, output: ValueBase):
        self._outputs.add(output)


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


class UnsupportedVersionException(Exception):
    def __init__(self, required_major, required_minor):
        super().__init__("Required API version (%s, %s), while supported version is (%s, %s)" %
                         (required_major, required_minor, VERSION_MAJOR, VERSION_MINOR))


class PlanExecutor:
    plan: Plan
    actions: Set[Action] = set()
    values: Set[ValueBase] = set()
    #build_contexts: dict[PurePosixPath, set[BuildImageAction]] = dict()

    def __init__(self, plan):
        self.plan = plan
        required_major, required_minor = self.plan.required_api
        if required_major > VERSION_MAJOR or (required_major == VERSION_MAJOR and required_minor > VERSION_MINOR):
            raise UnsupportedVersionException(required_major, required_minor)
        self._prepare()

    def _prepare(self):
        """
        Populate internal data structures before executing a plan
        """

        # table of containing directories (to add implicit dependencies to image builds)
        directories: dict[PurePosixPath, set[FileValue]] = dict()

        # map plan elements to values
        v: dict[Any, ValueBase] = dict()
        # map plan elements to actions
        a: dict[Any, Action] = dict()

        # Create FileValues for WorkFiles found in plan
        for workfile in self.plan.files():
            value = FileValue(workfile)
            v[workfile] = value
            dir = workfile.posix_path.parent
            if dir not in directories:
                directories[dir] = set()
            directories[dir].add(value)

        for image in self.plan.images():
            if image.pull_from_registry:
                image_value = RegistryImageValue(image)
                pull_image_action = PullImageAction(image)
                pull_image_action.set_output_image(image_value)
                v[image] = image_value
                a[image] = pull_image_action
            else:
                image_value = ImageToBuildValue(image)
                build_image_action = BuildImageAction(image)
                build_image_action.set_output_image(image_value)
                v[image] = image_value
                a[image] = build_image_action
                # if context dir contains any WorkFiles, add corresponding FileValues as dependencies
                for dir in directories.keys():
                    if dir.is_relative_to(image_value._plan_element.build_from_context):
                        for file_value in directories[dir]:
                            build_image_action.add_input(file_value)

        for exec in self.plan.execs():
            image_value = v[exec.image]
            if not isinstance(image_value, ImageValue):
                raise Exception("not an ImageValue %s" % image_value)
            exec_action = ExecAction(exec, image_value)
            a[exec] = exec_action
            for input in exec.inputs:
                exec_action.add_input(v[input.workfile])
            for output in exec.outputs:
                exec_action.add_output(v[output.workfile])

        self.actions = set(a.values())
        self.values = set(v.values())

    def update(self, context):
        INFO("update")
        for value in self.values:
            value.prepare(context)

        runlist = self.toposorted_actions()
        for action in runlist:
            if any(output.needs_update(context) for output in action.outputs()):
                action.run(context)

    def toposorted_actions(self) -> Iterable[Action]:
        """
        Return topologically sorted list of actions
        """
        # Here we execute two "nanopasses" (a term borrowed from compiler implementation)
        #
        # 1. Traverse a values-and-actions graph, reducing it to a dependency graph containing actions
        #
        # 2. Perform a toposort over actions (using Kahn's algorithm https://en.wikipedia.org/wiki/Topological_sorting)
        #
        # Q: Maybe reuse https://github.com/pombredanne/bitbucket.org-ericvsmith-toposort


        # 1. Dependency graph representation optimized for toposort
        o: dict[Action, set[Action]] = {}  # for actions: action -> set of outgoing dependency edges
        i: dict[Action, set[Action]] = {}  # for actions: action -> set of incoming dependency edges

        # set of nodes without incoming edges
        s: Set[Action] = set()

        # 1. Transform execution plan into dependency graph
        for action in self.actions:
            # if action does not depend on any other action, add it to set s
            if all(input.producer() is None for input in action.inputs()):
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

        # 2. Now run Kahn's algorithm (could be separated from previous to improve abstraction)
        # resulting list
        l = []

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










