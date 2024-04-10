import io
import json
import re
import sys
import threading
from pathlib import PurePosixPath, Path, PurePath, PosixPath, PureWindowsPath, WindowsPath
import git

import spec_parser
from common import CommandLineOptions

MNB_RUN = PurePosixPath("/mnb/run")

from docker import DockerClient, from_env
from docker.types import Mount
from docker.utils.socket import next_frame_header, read_exactly

from fancy_output import FancyOutput
from spec import *
from errors import UnexpectedActionType, IncompatibleValueAndThrough, ConflictingMounts, \
    ConflictingEnvironmentAssignements, UnexpectedInputThroughType, UnexpectedOutputThroughType
from plan import toposort_actions

class Context:
    client: DockerClient
    fancy_output: FancyOutput
    context_absolute_path_on_host: PurePath
    context_absolute_path_for_mnb: Path
    #config_file_path: Path

    def __init__(self, cliopts: CommandLineOptions):
        self.client = from_env()
        self.fancy_output = FancyOutput(sys.stdout)

        if cliopts.windows_host:
            host_pure_path_class = PureWindowsPath
            host_path_class = WindowsPath
        else:
            host_pure_path_class = PurePosixPath
            host_path_class = PosixPath

        self.context_absolute_path_on_host = host_pure_path_class(cliopts.rootabspath or ".")

        if cliopts.dev_mode:
            self.context_absolute_path_for_mnb = host_path_class(cliopts.rootabspath)
        else:
            self.context_absolute_path_for_mnb = PosixPath("/mnb/run")

        #self.config_file_path = self.context_absolute_path_for_mnb / cliopts.config_file

def execute_spec(spec: Spec, context: Context):
    if spec.description:
        context.fancy_output.phase(spec.description)
    context.fancy_output.phase(f"Actions to execute: {len(spec.actions)}")
    toposorted_actions = toposort_actions(spec)
    last_result = None
    for index, action in enumerate(toposorted_actions):
        context.fancy_output.phase(f"Action {index + 1}/{len(toposorted_actions)}")
        last_result = execute_action(action, context)
    return last_result


def execute_action(action, context):
    if isinstance(action, PullImage):
        return execute_pull_image(action, context)
    elif isinstance(action, BuildImage):
        return execute_build_image(action, context)
    elif isinstance(action, Exec):
        return execute_exec(action, context)
    else:
        raise UnexpectedActionType(action)


def execute_build_image(action: BuildImage, context: Context):
    if action.from_git:
        context.fancy_output.phase(f"fetch from git repo {action.from_git.repo} rev {action.from_git.rev}")
        repo_dir = re.sub("[^a-zA-Z0-9.-]+", "-", action.from_git.repo)
        repo_path = context.context_absolute_path_for_mnb / ".mnb" / "repo" / repo_dir
        if Path(repo_path).exists():
            context.fancy_output.progress(f"use existing working copy")
            repo = git.Repo(str(repo_path))
            origin = repo.remote('origin')
        else:
            context.fancy_output.progress(f"create new working copy")
            ensure_writable_dir(repo_path)
            repo = git.Repo.init(str(repo_path))
            origin = repo.create_remote('origin', action.from_git.repo)
        origin.fetch()
        context.fancy_output.success(f"fetched to {repo_path}")
        repo.git.checkout(action.from_git.rev)
        context_path = context.context_absolute_path_on_host / ".mnb" / "repo" / repo_dir / action.context_path
    else:
        context_path = context.context_absolute_path_on_host / action.context_path
    context.fancy_output.phase(f"Build image {action.image_name}")
    (image, stream) = context.client.images.build(tag=action.image_name,
                                                  path=str(context_path),
                                                  dockerfile=action.dockerfile_path,
                                                  buildargs=action.build_args)
    for i in stream:
        if 'stream' in i:
            context.fancy_output.progress(i['stream'], prefix=f"build {action.image_name}: ")
        elif 'aux' in i:
            context.fancy_output.success(str(i['aux']), prefix=f"build {action.image_name}: ")

def execute_pull_image(action: PullImage, context: Context):
    context.fancy_output.phase(f"Pull image {action.image_name}")
    parts = action.image_name.split(":")
    repository = parts[0]
    if len(parts) > 1:
        tag = parts[1]
    else:
        tag = None
    for line in context.client.api.pull(repository, tag=tag, stream=True, decode=True):
        #context.fancy_output.progress(f"{line.get('status', '')} {line.get('progress','')}")
        context.fancy_output.progress(f"{line}", prefix=f"pull {action.image_name}: ")

def execute_exec(action: Exec, context: Context):
    context.fancy_output.phase(f"exec {action.image_name} {action.command}")
    mounts: Dict[str, Mount] = dict()
    stdin_inputs = [] # stdin sources (would be concatenated together)
    stdout_outputs = []   # stdout destinations (output would be fanned out)
    stderr_outputs = []  # stderr destinations (output would be fanned out)
    file_outputs = []
    environment = {}
    for inp in action.inputs:
        if isinstance(inp.through, ThroughFile):
            if isinstance(inp.value, File):
                if inp.through.path in mounts:
                    raise ConflictingMounts(action, inp.through.path)
                else:
                    mounts[inp.through.path] = (Mount(source=str(context.context_absolute_path_on_host / inp.value.path),
                                                      target=str(MNB_RUN / inp.through.path),
                                                      type='bind',
                                                      read_only=True))
            else:
                raise IncompatibleValueAndThrough(action, inp.value, inp.through)
        elif isinstance(inp.through, ThroughDir):
            if isinstance(inp.value, Dir):
                if inp.through.path in mounts:
                    raise ConflictingMounts(action, inp.through.path)
                else:
                    mounts[inp.through.path] = (Mount(source=str(context.context_absolute_path_on_host / inp.value.path),
                                                      target=str(MNB_RUN / inp.through.path),
                                                      type='bind',
                                                      read_only=True))
            else:
                raise IncompatibleValueAndThrough(action, inp.value, inp.through)
        elif isinstance(inp.through, ThroughStdin):
            if isinstance(inp.value, File):
                stdin_inputs.append(inp)
            else:
                raise IncompatibleValueAndThrough(action, inp.value, inp.through)
        elif isinstance(inp.through, ThroughEnvironment):
            if inp.through.name in environment:
                raise ConflictingEnvironmentAssignements(action, inp.through.name)
            if isinstance(inp.value, File):
                with open(context.context_absolute_path_for_mnb / inp.value.path) as input_file:
                    # for now we ignore encoding issues
                    s = input_file.read()
                    environment[inp.through.name] = s
            else:
                raise IncompatibleValueAndThrough(action, inp.value, inp.through)
        else:
            raise UnexpectedInputThroughType(inp.through)
    for out in action.outputs:
        if isinstance(out.through, ThroughFile):
            if (isinstance(out.value, File)):
                file_outputs.append(out)
            else:
                raise IncompatibleValueAndThrough(action, out.value, out.through)
        elif isinstance(out.through, ThroughDir):
            # output directories not supported for now
            raise UnexpectedOutputThroughType(out.through)
        elif isinstance(out.through, ThroughStdout):
            if (isinstance(out.value, File)):
                stdout_outputs.append(out)
            else:
                raise IncompatibleValueAndThrough(action, out.value, out.through)
        elif isinstance(out.through, ThroughStderr):
            if (isinstance(out.value, File)):
                stderr_outputs.append(out)
            else:
                raise IncompatibleValueAndThrough(action, out.value, out.through)
        else:
            raise UnexpectedOutputThroughType(out.through)
    # create temporary dir to use as a current dir during container run
    temp_dir_on_host = context.context_absolute_path_on_host / ".mnb" / "context" / str(id(action))
    temp_dir_for_mnb = context.context_absolute_path_for_mnb / ".mnb" / "context" / str(id(action))
    ensure_writable_dir(temp_dir_for_mnb)
    all_mounts = list(mounts.values())
    all_mounts.append(Mount(source=str(temp_dir_on_host),
                      target=str(MNB_RUN),
                      type="bind",
                      read_only=False))
    # detrmine workdir container parameter
    if action.workdir:
        workdir = MNB_RUN / action.workdir
    else:
        workdir = MNB_RUN
    # create container, but do not start yet (we need to attach to it first)
    container = context.client.containers.create(
        action.image_name,
        command=action.command,
        mounts=all_mounts,
        working_dir=str(workdir),
        detach=True,
        stdin_open=True)
    # attach to socket
    docker_socket = container.attach_socket(params=dict(interactive=True,
                                                        stdout=True,
                                                        stderr=True,
                                                        stdin=True,
                                                        stream=True,
                                                        demux=True))
    # initialize in-memory buffers for stdio streams
    # TODO: For output streams, writes could be redirected to output files via fan-out stream
    stdout_stream = io.BytesIO()
    stderr_stream = io.BytesIO()
    # TODO: for stdin, reads could be orchestrated via chained stream source
    stdin_data = []
    for inp in stdin_inputs:
        with open(str(context.context_absolute_path_for_mnb / inp.value.path), "rb") as f:
            stdin_data.append(f.read())
    stdin_stream = io.BytesIO(b"".join(stdin_data))
    # threads to receive and send stdio streams via docker socket
    sender_thread = threading.Thread(target=socket_sender, args=(docker_socket._sock, stdin_stream))
    receiver_thread = threading.Thread(target=socket_receiver, args=(docker_socket._sock, stdout_stream, stderr_stream))
    # now we are ready to start the container
    container.start()
    receiver_thread.start()
    sender_thread.start()
    # wait for sender and receiver threads to terminate
    receiver_thread.join()
    sender_thread.join()
    # update container status
    container.reload()
    exit_code = container.attrs['State']['ExitCode']
    container.stop()
    container.remove()
    if len(stderr_stream.getvalue()) > 0:
        context.fancy_output.failure(stderr_stream.getvalue().decode('utf8'), prefix=f"{action.image_name} stderr: ")
    context.fancy_output.progress(f"Stdout length {len(stdout_stream.getvalue())}", prefix=f"{action.image_name}: ")
    if exit_code != 0:
        context.fancy_output.failure(f"Exit code {exit_code}", prefix=f"{action.image_name}: ")
        raise Exception(f"Exit code {exit_code}")
    # copy output files
    # TODO: use more efficient file copy
    for file_output in file_outputs:
        with Path(temp_dir_for_mnb / file_output.through.path).open('rb') as src:
            data = src.read()
            output_path = context.context_absolute_path_for_mnb / file_output.value.path
            ensure_writable_dir(output_path.parent)
            with output_path.open('wb') as dst:
                dst.write(data)
    for stdout_output in stdout_outputs:
        output_path = context.context_absolute_path_for_mnb / stdout_output.value.path
        ensure_writable_dir(output_path.parent)
        with Path(output_path).open('wb') as dst:
            dst.write(stdout_stream.getvalue())
    for stderr_output in stderr_outputs:
        output_path = context.context_absolute_path_for_mnb / stderr_output.value.path
        ensure_writable_dir(output_path.parent)
        with Path(output_path).open('wb') as dst:
            dst.write(stderr_stream.getvalue())
    context.fancy_output.success(f"command {action.command} succeed", prefix=f"{action.image_name}: ")
    return stdout_stream.getvalue()


def socket_receiver(sock, stdout_stream, stderr_stream):
    while True:
        stream, length = next_frame_header(sock)
        if stream == -1:
            break
        received = read_exactly(sock, length)
        #print(f"stream {stream}: {received.decode('utf-8')}")
        if stream == 1:
            stdout_stream.write(received)
        else:
            stderr_stream.write(received)

def socket_sender(sock, stdin_stream):
    n = 512
    buffer = b""
    while True:
        if len(buffer) == 0:
            buffer = stdin_stream.read(n)
            if len(buffer) == 0:
                break
        # todo: use sendall
        sent = sock.send(buffer)
        buffer = buffer[sent:]

def ensure_writable_dir(param):
    path = Path(param)
    if path.exists() and not path.is_dir():
        raise Exception("Not a directory: %s" % path)
    path.mkdir(exist_ok=True, parents=True)
    return path

def update(cliopts: CommandLineOptions):
    context = Context(cliopts)
    workspace_file_name = "mnb-workspace.json"
    workspace_path = context.context_absolute_path_for_mnb / workspace_file_name
    if not workspace_path.exists():
        context.fancy_output.failure(f"Workspace file {workspace_file_name} not found")
        sys.exit(1)
    with workspace_path.open('rb') as workspace_file:
        workspace_json = json.load(workspace_file)
        if 'description' in workspace_json:
            context.fancy_output.phase(workspace_json['description'])
        spec_version = workspace_json.get('spec_version')
        for generator_elem in workspace_json.get('generators', []):
            if 'include' in generator_elem:
                include_path = generator_elem.get('include').get('path')
                with (context.context_absolute_path_for_mnb / include_path).open('r') as generator_file:
                    generator = spec_parser.parse_spec(json.load(generator_file))
                    generator_output = execute_spec(generator, context)
                    spec = spec_parser.parse_spec(json.loads(generator_output))
                    execute_spec(spec, context)
            elif 'generator' in generator_elem:
                generator_json = generator_elem.get('generator')
                if 'spec_version' not in generator_json:
                    generator_json['spec_version'] = spec_version
                generator = spec_parser.parse_spec(generator_json)
                generator_output = execute_spec(generator, context)
                spec = spec_parser.parse_spec(json.loads(generator_output))
                execute_spec(spec, context)
            else:
                raise Exception(f"Invalid generator element {json.dumps(generator_elem, indent=2)}")