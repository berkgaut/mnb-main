import json
import sys

import spec

def spec_to_json(s: spec.Spec):
    return {
        "spec_version": f"{s.spec_version[0]}.{s.spec_version[1]}",
        "actions": list(map(action_to_json, s.actions))
    }

class WriterError(Exception):
    pass

def action_to_json(action: spec.Action):
    if isinstance(action, spec.PullImage):
        action_json = {"pull_image": {"image_name": action.image_name}}
        return action_json
    elif isinstance(action, spec.BuildImage):
        action_json = {"build_image": {
            "image_name": action.image_name,
            "context_path": action.context_path,
        }}
        if action.dockerfile_path:
            action_json['build_image']['dockerfile_path'] = action.dockerfile_path
        if action.build_args:
            action_json['build_image']['build_args'] = [{"name": key, "value": value} for (key, value) in action.build_args.items()]
        if action.from_git:
            action_json['build_image']['from_git'] = {"repo": action.from_git.repo, "rev": action.from_git.rev}
        if action.extra_tags:
            action_json['build_image']['extra_tags'] = action.extra_tags
        return action_json
    elif isinstance(action, spec.Exec):
        action_json = {"exec": {
            "image_name": action.image_name
        }}
        if action.command:
            action_json['exec']['command'] = action.command
        if action.entrypoint:
            action_json['exec']['entrypoint'] = action.entrypoint
        if action.workdir:
            action_json['exec']['workdir'] = action.workdir
        if len(action.inputs) > 0:
            action_json['exec']['inputs'] = list(map(input_to_json, action.inputs))
        if len(action.outputs) > 0:
            action_json['exec']['outputs'] = list(map(output_to_json, action.outputs))
        return action_json
    else:
        raise WriterError(f"Unexpected action type {type(action)}")

def input_to_json(input: spec.Input):
    through = input.through
    if isinstance(through, spec.ThroughFile):
        through_json = {"file": {"path": through.path}}
    elif isinstance(through, spec.ThroughDir):
        through_json = {"dir": {"path": through.path}}
    elif isinstance(through, spec.ThroughStdin):
        through_json = {"stream": {"name": "STDIN"}}
    elif isinstance(through, spec.ThroughEnvironment):
        through_json = {"environment": {"name": through.name}}
    else:
        raise WriterError(f"Unexpected input through type {type(through)}")
    return {"value": value_to_json(input.value), "through": through_json}

def output_to_json(output: spec.Output):
    through = output.through
    if isinstance(through, spec.ThroughFile):
        through_json = {"file": {"path": through.path}}
    elif isinstance(through, spec.ThroughDir):
        through_json = {"dir": {"path": through.path}}
    elif isinstance(through, spec.ThroughStdout):
        through_json = {"stream": {"name": "STDOUT"}}
    elif isinstance(through, spec.ThroughStderr):
        through_json = {"stream": {"name": "STDERR"}}
    else:
        raise WriterError(f"Unexpected output through type {type(through)}")
    return {"value": value_to_json(output.value), "through": through_json}

def value_to_json(value: spec.Value):
    if isinstance(value, spec.File):
        return {"file": {"path": value.path}}
    elif isinstance(value, spec.Dir):
        return {"dir": {"path": value.path}}
    else:
        raise WriterError(f"Unexpected value type {type(value)}")

def print_spec_json(s: spec.Spec):
    json.dump(spec_to_json(s), sys.stdout)


