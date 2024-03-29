import re

from apispec import BasePlugin

from apispec.yaml_utils import load_yaml_from_docstring
from marshmallow import class_registry

from combojsonapi.utils import schema_not_in_registry, create_schema_name

RE_URL = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def flaskpath2swagger(path):
    """Convert a Flask URL rule to an OpenAPI-compliant path.

    :param str path: Flask path template.
    """
    return RE_URL.sub(r"{\1}", path)


class RestfulPlugin(BasePlugin):

    def init_spec(self, spec):
        super().init_spec(spec)
        self.spec = spec

    def _ref_to_spec(self, data):
        """
        Get spec from description

        :param data:
        :return:
        """
        if isinstance(data, list):
            for i_v in data:
                self._ref_to_spec(i_v)
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    for i_v in v:
                        self._ref_to_spec(i_v)
                if isinstance(v, dict):
                    self._ref_to_spec(v)
                elif k == "$ref":
                    name_schema = v.split("/")[-1]
                    schema = class_registry.get_class(name_schema)
                    name_schema = create_schema_name(schema=schema)
                    if name_schema not in self.spec.components.schemas:
                        self.spec.components.schema(name_schema, schema=schema)
                    data[k] = "/".join(v.split("/")[:-1] + [name_schema])

    def process_query_params_spec(self, schema_ref_name: str):
        if schema_not_in_registry(schema_ref_name):
            # probably schema name was updated from e.g. `UserSchema` to `User` by `_ref_to_spec`
            # try to recover its name if first option was not found
            schema_ref_name = f"{schema_ref_name}Schema"

        new_parameters = []
        name_schema = create_schema_name(name_schema=schema_ref_name)
        if name_schema in self.spec.components.schemas:
            for i_name, i_value in self.spec.components.schemas[name_schema]["properties"].items():
                new_parameter = {
                    "name": i_name,
                    "in": "query",
                    "type": i_value.get("type"),
                    "description": i_value.get("description", ""),
                }
                if "example" in i_value:
                    new_parameter["example"] = i_value["example"]
                if "items" in i_value:
                    new_items = {
                        "type": i_value["items"].get("type"),
                    }
                    if "enum" in i_value["items"]:
                        new_items["enum"] = i_value["items"]["enum"]
                    new_parameter.update({"items": new_items})
                new_parameters.append(new_parameter)
        return new_parameters

    def operation_helper(self, path=None, operations=None, **kwargs):
        """
        If query params have a marshmallow schema reference,
        get params from the schema from the top level (no Nested)
        """
        resource = kwargs.get("resource", None)
        for m in getattr(resource, "methods", []):
            m = m.lower()
            f = getattr(resource, m)
            m_ops = load_yaml_from_docstring(f.__doc__)
            if m_ops:
                operations.update({m: m_ops})
            self._ref_to_spec(m_ops)
        for method, val in operations.items():
            for index, parametr in enumerate(val["parameters"] if "parameters" in val else []):
                if (
                    "in" in parametr and parametr["in"] == "query"
                    and "schema" in parametr and "$ref" in parametr["schema"]
                ):
                    name_schema = parametr["schema"]["$ref"].split("/")[-1]
                    new_parameters = self.process_query_params_spec(name_schema)
                    del val["parameters"][index]
                    val["parameters"].extend(new_parameters)

    def path_helper(self, path=None, operations=None, urls=None, resource=None, **kwargs):
        """Path helper that allows passing a Flask view function."""
        path = flaskpath2swagger(urls[0]) if urls else flaskpath2swagger(path)
        return path
