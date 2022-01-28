import inspect
import typing
from typing import Optional

class AnnotationBase:
    pass


class Example:
    __json_tag__ = "this_is_foo"

    foo: str = ""
    __foo_json_tag__ = "custom_foo"

    bar: Optional[int] = None

    baz: Optional[str]

    def __init__(self, foo, bar):
        self.foo = foo
        self.bar = bar


def to_json(x):
    if type(x) in {int, float, str}:
        return x
    if x is None:
        return None
    elif type(x) is dict:
        return {k: to_json(v) for (k, v) in x.items()}
    elif type(x) is list:
        return [to_json(x) for x in x]
    else:
        tag = getattr(x, '__json_tag__', x.__class__.__name__.lower())
        result = dict()
        for (name, t) in x.__annotations__.items():
            field_name = getattr(x, f"__{name}_json_tag__", name)
            field_value = to_json(getattr(x, name, None))
            result[field_name] = field_value
            print(name, t)
        return {tag: result}


class TypeMismatch(Exception):
    def __init__(self, context, expected_type, value):
        self.context = context
        self.expected_type = expected_type
        self.value = value

    def __str__(self):
        return "Type mismatch context %(context)s expected type %(expected_type)s value %(value)s" % self.__dict__


# вот в этой статье лежат несколько мапперов, которые делают вроде то, что мне нужно https://testdriven.io/blog/python-type-checking/
# конкретно pydantic, marshmallow, typical

class Foo: pass

def from_json(ctx, data: "asdasdasd", t: Foo()):
    if t in {int, float, str}:
        if type(data) == t:
            return data
        else:
            raise TypeMismatch(ctx, t, data)
    # if typing.Optional
    #if data is None and t \




print(to_json(Example("gaga", 12)))
