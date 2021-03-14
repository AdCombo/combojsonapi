from http import HTTPStatus
from typing import Dict, Any, Set, List, Union, Tuple, Generator

from apispec import APISpec
from apispec.exceptions import APISpecError
from apispec.ext.marshmallow import (
    MarshmallowPlugin,
    OpenAPIConverter,
    make_schema_key,
    resolve_schema_cls,
    resolve_schema_instance,
)
from marshmallow import fields, Schema
from flask_combo_jsonapi import Api
from flask_combo_jsonapi.plugin import BasePlugin
from flask_combo_jsonapi.resource import ResourceList, ResourceDetail, Resource
from flask_combo_jsonapi.utils import SPLIT_REL

from combojsonapi.spec.apispec import DocBlueprintMixin
from combojsonapi.spec.compat import APISPEC_VERSION_MAJOR
from combojsonapi.spec.plugins_for_apispec import RestfulPlugin
from combojsonapi.utils import Relationship, create_schema_name, status


class ApiSpecPlugin(BasePlugin, DocBlueprintMixin):
    """Плагин для связки json_api и swagger"""

    def __init__(self, app=None, spec_kwargs=None, decorators=None, tags: Dict[str, str] = None):
        """

        :param spec_kwargs:
        :param decorators:
        :param tags: {'<name tag>': '<description tag>'}
        """
        self.decorators_for_autodoc = decorators or tuple()
        self.spec_kwargs = spec_kwargs if spec_kwargs is not None else {}
        self.spec = None
        self.spec_tag = {}
        self.spec_schemas = {}
        self.app = None
        self._fields = []
        # Use lists to enforce order
        self._fields = []
        self._converters = []

        # Инициализация ApiSpec
        self.app = app
        self._app = app
        # Initialize spec
        openapi_version = app.config.get("OPENAPI_VERSION", "2.0")
        openapi_major_version = int(openapi_version.split(".")[0])
        if openapi_major_version < 3:
            base_path = app.config.get("APPLICATION_ROOT")
            # Don't pass basePath if '/' to avoid a bug in apispec
            # https://github.com/marshmallow-code/apispec/issues/78#issuecomment-431854606
            # TODO: Remove this condition when the bug is fixed
            if base_path != "/":
                self.spec_kwargs.setdefault("basePath", base_path)
        self.spec_kwargs.update(app.config.get("API_SPEC_OPTIONS", {}))
        self.spec = APISpec(
            app.name,
            app.config.get("API_VERSION", "1"),
            openapi_version=openapi_version,
            plugins=[MarshmallowPlugin(), RestfulPlugin()],
            **self.spec_kwargs,
        )

        tags = tags if tags else {}
        for tag_name, tag_description in tags.items():
            self.spec_tag[tag_name] = {"name": tag_name, "description": tag_description, "add_in_spec": False}
            self._add_tags_in_spec(self.spec_tag[tag_name])

    def after_init_plugin(self, *args, app=None, **kwargs):
        # Register custom fields in spec
        for args in self._fields:
            self.spec.register_field(*args)
        # Register custom converters in spec
        for args in self._converters:
            self.spec.register_converter(*args)

        # Initialize blueprint serving spec
        self._register_doc_blueprint()

    def after_route(
        self,
        resource: Union[ResourceList, ResourceDetail] = None,
        view=None,
        urls: Tuple[str] = None,
        self_json_api: Api = None,
        tag: str = None,
        default_parameters=None,
        default_schema: Schema = None,
        **kwargs,
    ) -> None:
        """

        :param resource:
        :param view:
        :param urls:
        :param self_json_api:
        :param str tag: тег под которым стоит связать этот ресурс
        :param default_parameters: дефолтные поля для ресурса в сваггер (иначе просто инициализируется [])
        :param Schema default_schema: схема, которая подставиться вместо схемы в стили json api
        :param kwargs:
        :return:
        """
        # Register views in API documentation for this resource
        # resource.register_views_in_doc(self._app, self.spec)
        # Add tag relative to this resource to the global tag list

        # We add definitions (models) to the apiscpec
        if resource.schema:
            self._add_definitions_in_spec(resource.schema)

        # We add tags to the apiscpec
        tag_name = view.title()
        if tag is None and view.title() not in self.spec_tag:
            dict_tag = {"name": view.title(), "description": "", "add_in_spec": False}
            self.spec_tag[dict_tag["name"]] = dict_tag
            self._add_tags_in_spec(dict_tag)
        elif tag:
            tag_name = self.spec_tag[tag]["name"]

        urls = urls if urls else tuple()
        for i_url in urls:
            self._add_paths_in_spec(
                path=i_url,
                resource=resource,
                default_parameters=default_parameters,
                default_schema=default_schema,
                tag_name=tag_name,
                **kwargs,
            )

    @property
    def param_id(self) -> dict:
        return {
            "in": "path",
            "name": "id",
            "required": True,
            "type": "integer",
            "format": "int32",
        }

    @classmethod
    def _get_operations_for_all(cls, tag_name: str, default_parameters: list) -> Dict[str, Any]:
        """
        Creating base dict

        :param tag_name:
        :param default_parameters:
        :return:
        """
        return {
            "tags": [tag_name],
            "produces": ["application/json"],
            "parameters": default_parameters if default_parameters else [],
        }

    @classmethod
    def __get_parameters_for_include_models(cls, resource: Resource) -> dict:
        fields_names = [
            i_field_name
            for i_field_name, i_field in resource.schema._declared_fields.items()
            if isinstance(i_field, Relationship)
        ]
        models_for_include = ",".join(fields_names)
        example_models_for_include = "\n".join([f"`{f}`" for f in fields_names])
        return {
            "default": models_for_include,
            "name": "include",
            "in": "query",
            "format": "string",
            "required": False,
            "description": f"Related relationships to include.\nAvailable:\n{example_models_for_include}",
        }

    @classmethod
    def __get_parameters_for_sparse_fieldsets(cls, resource: Resource, description: str) -> dict:
        # Sparse Fieldsets
        return {
            "name": f"fields[{resource.schema.Meta.type_}]",
            "in": "query",
            "type": "array",
            "required": False,
            "description": description.format(resource.schema.Meta.type_),
            "items": {"type": "string", "enum": list(resource.schema._declared_fields.keys())},
        }

    def __get_parameters_for_declared_fields(self, resource, description) -> Generator[dict, None, None]:
        type_schemas = {resource.schema.Meta.type_}
        for i_field_name, i_field in resource.schema._declared_fields.items():
            if not (isinstance(i_field, Relationship) and i_field.schema.Meta.type_ not in type_schemas):
                continue
            schema_name = create_schema_name(schema=i_field.schema)
            new_parameter = {
                "name": f"fields[{i_field.schema.Meta.type_}]",
                "in": "query",
                "type": "array",
                "required": False,
                "description": description.format(i_field.schema.Meta.type_),
                "items": {
                    "type": "string",
                    "enum": list(self.spec.components.schemas[schema_name]["properties"].keys()),
                },
            }
            type_schemas.add(i_field.schema.Meta.type_)
            yield new_parameter

    @property
    def __list_filters_data(self) -> tuple:
        return (
            {
                "default": 1,
                "name": "page[number]",
                "in": "query",
                "format": "int64",
                "required": False,
                "description": "Page offset",
            },
            {
                "default": 10,
                "name": "page[size]",
                "in": "query",
                "format": "int64",
                "required": False,
                "description": "Max number of items",
            },
            {"name": "sort", "in": "query", "format": "string", "required": False, "description": "Sort",},
            {
                "name": "filter",
                "in": "query",
                "format": "string",
                "required": False,
                "description": "Filter (https://flask-combo-jsonapi.readthedocs.io/en/latest/filtering.html)",
            },
        )

    @classmethod
    def _update_parameter_for_field_spec(cls, new_param: dict, fld_sped: dict) -> None:
        """
        :param new_param:
        :param fld_sped:
        :return:
        """
        if "items" in fld_sped:
            new_items = {
                "type": fld_sped["items"].get("type"),
            }
            if "enum" in fld_sped["items"]:
                new_items["enum"] = fld_sped["items"]["enum"]
            new_param.update({"items": new_items})

    def __get_parameter_for_not_nested(self, field_name, field_spec) -> dict:
        new_parameter = {
            "name": f"filter[{field_name}]",
            "in": "query",
            "type": field_spec.get("type"),
            "required": False,
            "description": f"{field_name} attribute filter",
        }
        self._update_parameter_for_field_spec(new_parameter, field_spec)
        return new_parameter

    def __get_parameter_for_nested_with_filtering(self, field_name, field_jsonb_name, field_jsonb_spec):
        new_parameter = {
            "name": f"filter[{field_name}{SPLIT_REL}{field_jsonb_name}]",
            "in": "query",
            "type": field_jsonb_spec.get("type"),
            "required": False,
            "description": f"{field_name}{SPLIT_REL}{field_jsonb_name} attribute filter",
        }
        self._update_parameter_for_field_spec(new_parameter, field_jsonb_spec)
        return new_parameter

    def __get_parameters_for_nested_with_filtering(self, field, field_name) -> Generator[dict, None, None]:
        # Allow JSONB filtering
        field_schema_name = create_schema_name(schema=field.schema)
        component_schema = self.spec.components.schemas[field_schema_name]
        for i_field_jsonb_name, i_field_jsonb in field.schema._declared_fields.items():
            i_field_jsonb_spec = component_schema["properties"][i_field_jsonb_name]
            if i_field_jsonb_spec.get("type") == "object":
                # Пропускаем создание фильтров для dict. Просто не понятно как фильтровать по таким
                # полям
                continue
            new_parameter = self.__get_parameter_for_nested_with_filtering(
                field_name, i_field_jsonb_name, i_field_jsonb_spec,
            )
            yield new_parameter

    def __get_list_resource_fields_filters(self, resource) -> Generator[dict, None, None]:
        schema_name = create_schema_name(schema=resource.schema)
        for i_field_name, i_field in resource.schema._declared_fields.items():
            i_field_spec = self.spec.components.schemas[schema_name]["properties"][i_field_name]
            if not isinstance(i_field, fields.Nested):
                if i_field_spec.get("type") == "object":
                    # Skip filtering by dicts
                    continue
                yield self.__get_parameter_for_not_nested(i_field_name, i_field_spec)
            elif getattr(i_field.schema.Meta, "filtering", False):
                yield from self.__get_parameters_for_nested_with_filtering(i_field, i_field_name)

    def _get_operations_for_get(self, resource, tag_name, default_parameters):
        operations_get = self._get_operations_for_all(tag_name, default_parameters)
        operations_get["responses"] = {
            **status[HTTPStatus.OK],
            **status[HTTPStatus.NOT_FOUND],
        }

        if issubclass(resource, ResourceDetail):
            operations_get["parameters"].append(self.param_id)

        if resource.schema is None:
            return operations_get

        description = "List that refers to the name(s) of the fields to be returned `{}`"

        operations_get["parameters"].extend(
            (
                self.__get_parameters_for_include_models(resource),
                self.__get_parameters_for_sparse_fieldsets(resource, description),
            )
        )
        operations_get["parameters"].extend(self.__get_parameters_for_declared_fields(resource, description))

        if issubclass(resource, ResourceList):
            operations_get["parameters"].extend(self.__list_filters_data)
            operations_get["parameters"].extend(self.__get_list_resource_fields_filters(resource))

        return operations_get

    def _get_operations_for_post(self, schema: dict, tag_name: str, default_parameters: list) -> dict:
        operations = self._get_operations_for_all(tag_name, default_parameters)
        operations["responses"] = {
            "201": {"description": "Created"},
            "202": {"description": "Accepted"},
            "403": {"description": "This implementation does not accept client-generated IDs"},
            "404": {"description": "Not Found"},
            "409": {"description": "Conflict"},
        }
        operations["parameters"].append(
            {
                "name": "POST body",
                "in": "body",
                "schema": schema,
                "required": True,
                "description": f"{tag_name} attributes",
            }
        )
        return operations

    def _get_operations_for_patch(self, schema: dict, tag_name: str, default_parameters: list) -> dict:
        operations = self._get_operations_for_all(tag_name, default_parameters)
        operations["responses"] = {
            "200": {"description": "Success"},
            "201": {"description": "Created"},
            "204": {"description": "No Content"},
            "403": {"description": "Forbidden"},
            "404": {"description": "Not Found"},
            "409": {"description": "Conflict"},
        }
        operations["parameters"].append(self.param_id)
        operations["parameters"].append(
            {
                "name": "POST body",
                "in": "body",
                "schema": schema,
                "required": True,
                "description": f"{tag_name} attributes",
            }
        )
        return operations

    def _get_operations_for_delete(self, tag_name: str, default_parameters: list) -> dict:
        operations = self._get_operations_for_all(tag_name, default_parameters)
        operations["parameters"].append(self.param_id)
        operations["responses"] = {
            "200": {"description": "Success"},
            "202": {"description": "Accepted"},
            "204": {"description": "No Content"},
            "403": {"description": "Forbidden"},
            "404": {"description": "Not Found"},
        }
        return operations

    def _add_paths_in_spec(
        self,
        path: str = "",
        resource: Any = None,
        tag_name: str = "",
        default_parameters: List = None,
        default_schema: Schema = None,
        **kwargs,
    ) -> None:
        operations = {}
        methods: Set[str] = {i_method.lower() for i_method in resource.methods}

        attributes = {}
        if resource.schema:
            attributes = self.spec.get_ref("schema", create_schema_name(resource.schema))
        schema = (
            default_schema
            if default_schema
            else {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                            },
                            "id": {
                                "type": "string",
                            },
                            "attributes": attributes,
                            "relationships": {
                                "type": "object",
                            },
                        },
                        "required": [
                            "type",
                        ],
                    },
                },
            }
        )

        if "get" in methods:
            operations["get"] = self._get_operations_for_get(resource, tag_name, default_parameters)
        if "post" in methods:
            operations["post"] = self._get_operations_for_post(schema, tag_name, default_parameters)
        if "patch" in methods:
            operations["patch"] = self._get_operations_for_patch(schema, tag_name, default_parameters)
        if "delete" in methods:
            operations["delete"] = self._get_operations_for_delete(tag_name, default_parameters)
        rule = None
        for i_rule in self.app.url_map._rules:
            if i_rule.rule == path:
                rule = i_rule
                break
        if APISPEC_VERSION_MAJOR < 1:
            self.spec.add_path(path=path, operations=operations, rule=rule, resource=resource, **kwargs)
        else:
            self.spec.path(path=path, operations=operations, rule=rule, resource=resource, **kwargs)

    def _add_definitions_in_spec(self, schema) -> None:
        """
        Add schema in spec
        :param schema: schema marshmallow
        :return:
        """
        name_schema = create_schema_name(schema)
        if name_schema not in self.spec_schemas and name_schema not in self.spec.components.schemas:
            self.spec_schemas[name_schema] = schema
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.definition(name_schema, schema=schema)
            else:
                self.spec.components.schema(name_schema, schema=schema)

    def _add_tags_in_spec(self, tag: Dict[str, str]) -> None:
        """
        Add tags in spec
        :param tag: {'name': '<name tag>', 'description': '<tag description>', 'add_in_spec': <added tag in spec?>}
        :return:
        """
        if tag.get("add_in_spec", True) is False:
            self.spec_tag[tag["name"]]["add_in_spec"] = True
            tag_in_spec = {"name": tag["name"], "description": tag["description"]}
            if APISPEC_VERSION_MAJOR < 1:
                self.spec.add_tag(tag_in_spec)
            else:
                self.spec.tag(tag_in_spec)


# Refactoring to get rid of warnings about already present schemas
# Creation of new schemas' names was changed
def resolve_nested_schema(self, schema):
    """Return the Open API representation of a marshmallow Schema.

    Adds the schema to the spec if it isn't already present.

    Typically will return a dictionary with the reference to the schema's
    path in the spec unless the `schema_name_resolver` returns `None`, in
    which case the returned dictoinary will contain a JSON Schema Object
    representation of the schema.

    :param schema: schema to add to the spec
    """
    schema_instance = resolve_schema_instance(schema)
    schema_key = make_schema_key(schema_instance)
    if schema_key not in self.refs:
        schema_cls = resolve_schema_cls(schema)
        name = self.schema_name_resolver(schema_cls)
        if not name:
            try:
                json_schema = self.schema2jsonschema(schema)
            except RuntimeError:
                raise APISpecError(
                    "Name resolver returned None for schema {schema} which is "
                    "part of a chain of circular referencing schemas. Please"
                    " ensure that the schema_name_resolver passed to"
                    " MarshmallowPlugin returns a string for all circular"
                    " referencing schemas.".format(schema=schema)
                )
            if getattr(schema, "many", False):
                return {"type": "array", "items": json_schema}
            return json_schema
        name = create_schema_name(schema=schema_instance)
        if name not in self.spec.components.schemas:
            self.spec.components.schema(name, schema=schema)
    return self.get_ref_dict(schema_instance)


OpenAPIConverter.resolve_nested_schema = resolve_nested_schema
