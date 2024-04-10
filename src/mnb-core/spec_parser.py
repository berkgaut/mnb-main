from typing import Optional

from jsonschema.validators import validate
import json
import spec

from errors import ParseError
import common

with (common.get_lib_path() / "spec-schema.json").open("r") as schema_file:
    schema = json.load(schema_file)

def parse_spec(parsed_json) -> spec.Spec:
    validate(parsed_json, schema)
    [maj_str, min_str] = parsed_json['spec_version'].split('.')
    spec_version = (int(maj_str), int(min_str))
    description = parsed_json.get('description')
    actions = map(parse_action, parsed_json['actions'])
    return spec.Spec(spec_version, list(actions), description)

def parse_action(parsed_json) -> 'spec.Action':
    if 'pull_image' in parsed_json:
        action_json = parsed_json['pull_image']
        image_name = action_json['image_name']
        return spec.PullImage(image_name)
    elif 'build_image' in parsed_json:
        action_json = parsed_json['build_image']
        image_name = action_json['image_name']
        context_path = action_json['context_path']
        dockerfile_path = action_json.get('dockerfile_path')
        build_args = { e['name']: e['value'] for e in action_json.get('build_args',[])}
        from_git = parse_from_git(action_json.get('from_git'))
        return spec.BuildImage(image_name, context_path, build_args, dockerfile_path, from_git)
    elif 'exec' in parsed_json:
        action_json = parsed_json['exec']
        image_name = action_json['image_name']
        command = action_json.get('command')
        entrypoint = action_json.get("entrypoint")
        workdir = action_json.get("workdir")
        inputs = map(parse_input, action_json.get('inputs', []))
        outputs = map(parse_output, action_json.get('outputs', []))
        return spec.Exec(image_name, command, entrypoint, workdir, list(inputs), list(outputs))
    else:
        raise ParseError(f"invalid action {parsed_json}")

def parse_from_git(parsed_json) -> Optional[spec.FromGit]:
    if parsed_json is None:
        return None
    else:
        return spec.FromGit(parsed_json['repo'], parsed_json['rev'])

def parse_input(parsed_json) -> 'spec.Input':
    value = parse_value(parsed_json['value'])
    through_json = parsed_json['through']
    if 'file' in through_json:
        path = through_json['file']['path']
        return spec.Input(value, spec.ThroughFile(path))
    elif 'dir' in through_json:
        path = through_json['dir']['path']
        return spec.Input(value, spec.ThroughDir(path))
    elif 'environment' in through_json:
        name = through_json['environment']['name']
        return spec.Input(value, spec.ThroughEnvironment(name))
    elif 'stream' in through_json:
        name = through_json['stream']['name']
        if name == 'STDIN':
            return spec.Input(value, spec.ThroughStdin())
        else:
            raise ParseError(f"Invalid input stream name {name}")
    else:
        raise ParseError(f"Invalid input through {through_json}")

def parse_output(parsed_json) -> 'spec.Output':
    value = parse_value(parsed_json['value'])
    through_json = parsed_json['through']
    if 'file' in through_json:
        path = through_json['file']['path']
        return spec.Output(value, spec.ThroughFile(path))
    elif 'dir' in through_json:
        path = through_json['dir']['path']
        return spec.Output(value, spec.ThroughDir(path))
    elif 'stream' in through_json:
        name = through_json['stream']['name']
        if name == 'STDOUT':
            return spec.Output(value, spec.ThroughStdout())
        elif name == 'STDERR':
            return spec.Output(value, spec.ThroughStderr())
        else:
            raise ParseError(f"Invalid output stream name {name}")
    else:
        raise ParseError(f"Invalid output through {through_json}")

def parse_value(parsed_json) -> 'spec.Value':
    if 'file' in parsed_json:
        path = parsed_json['file']['path']
        return spec.File(path)
    elif 'dir' in parsed_json:
        path = parsed_json['dir']['path']
        return spec.Dir(path)
    else:
        raise ParseError(f"Invalid value {parsed_json}")
