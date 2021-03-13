from marshmallow import class_registry, Schema
from apispec.ext.marshmallow import resolver
from apispec.ext.marshmallow.common import MODIFIERS

NO_ARGS_ERROR = "one of params `schema` or `name_schema` required"
INVALID_SCHEMA_TYPE = "can only make a schema key based on a Schema instance."
NO_SCHEMA_FOUND_ERROR = "No schema {schema_name!r} found in registry!"


def schema_not_in_registry(schema_name: str) -> bool:
    return schema_name not in class_registry._registry


def create_schema_name(schema=None, name_schema=None):
    if name_schema:
        if schema_not_in_registry(name_schema):
            raise ValueError(NO_SCHEMA_FOUND_ERROR.format(schema_name=name_schema))
        cls_schema = class_registry.get_class(name_schema)
        schema = cls_schema()
    elif schema:
        schema = schema if isinstance(schema, Schema) else schema()
        cls_schema = type(schema)
    else:
        raise ValueError(NO_ARGS_ERROR)

    if not isinstance(schema, Schema):
        raise TypeError(INVALID_SCHEMA_TYPE)

    modifiers = []
    for modifier in MODIFIERS:
        attribute = getattr(schema, modifier)
        if attribute:
            modifiers.append(f"{modifier}={attribute}")
    modifiers_str = ",".join(modifiers)
    if modifiers_str:
        modifiers_str = f"({modifiers_str})"
    name_cls_schema = resolver(cls_schema)
    return f"{name_cls_schema}{modifiers_str}"
