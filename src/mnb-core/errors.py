from spec import *

class ParseError(Exception):
    pass

class SpecSemanticError(Exception):
    pass

class ImageSpecConflict(SpecSemanticError):
    def __init__(self, action: Action, prev_definition: Action):
        super().__init__(f'Conflictiong definitions for image name {action.image_name}')
        self.action = action
        self.prev_definition = prev_definition


class MissingImageSpec(SpecSemanticError):
    def __init__(self, action: Action, image_name: str):
        super().__init__(f'Missing image definition for image name {image_name}')
        self.action = action
        self.image_name = image_name

class MissingProducer(SpecSemanticError):
    def __init__(self, value: Value):
        super().__init__(f'Missing producer for {value}')
        self.value = value

class UnexpectedActionType(SpecSemanticError):
    def __init__(self, action: Action):
        super().__init__(f'Invalid action type {type(action)}')
        self.action = action

class UnexpectedValueType(SpecSemanticError):
    def __init__(self, value: Value):
        super().__init__(f'Invalid value type {type(value)}')
        self.value = value

class ProducerConflict(SpecSemanticError):
    def __init__(self, value: Value, producer: Action, prev_producer: Action):
        super().__init__(f'Confliction producers for {value}')
        self.value = value
        self.producer = producer
        self.prev_producer = prev_producer


class IncompatibleValueAndThrough(SpecSemanticError):
    def __init__(self, action: Action, value: Value, through):
        super().__init__(f'Value type {type(Value)} not compatible with through {through} in action {action}')
        self.action = action
        self.value = value
        self.through = through

class ConflictingMounts(SpecSemanticError):
    def __init__(self, action: Action, path: str):
        super().__init__(f'Conflicting mounts on path {path} in action {action}')
        self.action = action
        self.path = path

class ConflictingEnvironmentAssignements(SpecSemanticError):
    def __init__(self, action: Action, name: str):
        super().__init__(f'Conflicting environment assignments for variable {name} in action {action}')
        self.action = action
        self.name = name

class UnexpectedInputThroughType(SpecSemanticError):
    def __init__(self, through):
        super().__init__(f'Invalid input through type {type(through)}')
        self.through = through

class UnexpectedOutputThroughType(SpecSemanticError):
    def __init__(self, through):
        super().__init__(f'Invalid output through type {type(through)}')
        self.through = through