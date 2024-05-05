# Build toposorted execution plan on top of spec
from graphlib import TopologicalSorter

from errors import ImageSpecConflict, MissingImageSpec, UnexpectedValueType, ProducerConflict
from spec import *

# could be rewritten using data-pipeline-like approach
# collect facts like "value X produced by action Y", group by value, then toposort.
# Values could be represented as pairs (type, id), for example ("image", "bash:5.2"), ("file", "mnb-generated/file.txt")

# !!! == or I could just implement dictionary/set key protocol for values. This protocol should be hash, eq, if I remember correctly

class ValueNode:
    value: Union[File, Dir, Image]
    consumers: set[Action]
    producer: Optional[Action]

    def __init__(self, value: Value):
        self.value = value
        self.consumers = set()
        self.producer = None

class ActionNode:
    action: Action
    input_value_nodes: set[ValueNode]

    def __init__(self, action):
        self.action = action
        self.input_value_nodes = set()

def toposort_actions(spec: Spec) -> List[Action]:
    images: Dict[str, ValueNode] = dict()
    files: Dict[str, ValueNode] = dict()
    dirs: Dict[str, ValueNode] = dict()
    action_nodes: set[ActionNode] = set()

    # Collect images produced by pull/build actions
    for action in spec.actions:
        if isinstance(action, (PullImage, BuildImage)):
            if action.image_name not in images:
                value = Image(action.image_name)
                value_node = ValueNode(value)
                images[action.image_name] = value_node
                images[action.image_name].producer = action
                action_node = ActionNode(action)
                action_nodes.add(action_node)
            else:
                raise ImageSpecConflict(action, prev_definition=images[action.image_name].producer)

    # Collect Exec dependencies
    for action in spec.actions:
        if isinstance(action, Exec):
            if action.image_name not in images:
                # images could be produced only by pull/build actions, which were analyzed on a previous step
                raise MissingImageSpec(action, action.image_name)
            images[action.image_name].consumers.add(action)
            action_node = ActionNode(action)
            action_node.input_value_nodes.add(images[action.image_name])
            action_nodes.add(action_node)
            for inp in action.inputs:
                if isinstance(inp.value, File):
                    if inp.value.path not in files:
                        files[inp.value.path] = ValueNode(inp.value)
                    files[inp.value.path].consumers.add(action)
                    action_node.input_value_nodes.add(files[inp.value.path])
                elif isinstance(inp.value, Dir):
                    if inp.value.path not in dirs:
                        dirs[inp.value.path] = ValueNode(inp.value)
                    dirs[inp.value.path].consumers.add(action)
                    action_node.input_value_nodes.add(dirs[inp.value.path])
                elif isinstance(inp.value, Image):
                    if inp.value.image_name not in images:
                        images[inp.value.image_name] = ValueNode(inp.value)
                    images[inp.value.image_name].consumers.add(action)
                    action_node.input_value_nodes.add(images[inp.value.image_name])
                else:
                    raise UnexpectedValueType(inp.value)
            for out in action.outputs:
                if isinstance(out.value, File):
                    if out.value.path not in files:
                        files[out.value.path] = ValueNode(out.value)
                    if files[out.value.path].producer is not None:
                        raise ProducerConflict(out.value, action, prev_producer=files[out.value.path].producer)
                    files[out.value.path].producer = action
                elif isinstance(out.value, Dir):
                    if out.value.path not in dirs:
                        dirs[out.value.path] = ValueNode(out.value)
                    if dirs[out.value.path].producer is not None:
                        raise ProducerConflict(out.value, action, prev_producer=files[out.value.path].producer)
                    dirs[out.value.path].producer = action
                else:
                    raise UnexpectedValueType(out.value)
    # Topologically sort
    ts = TopologicalSorter()
    for action_node in action_nodes:
        action = action_node.action
        predecessors = list(filter(lambda x: x is not None, map(lambda value_node: value_node.producer, action_node.input_value_nodes)))
        ts.add(action, *predecessors)
    return list(ts.static_order())

