from collections import OrderedDict
from unittest.mock import Mock, patch

import pytest
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from combojsonapi.spec import ApiSpecPlugin
from combojsonapi.spec.plugin import resolve_nested_schema
from combojsonapi.spec.plugins_for_apispec import RestfulPlugin
from combojsonapi.utils import create_schema_name
from tests.test_spec import SomeSchema, SomeModel, AnotherRelatedModelSchema, app, SomeResourceList, SomeResourceDetail

module_path = 'combojsonapi.spec.plugin'


class TestApiSpecPlugin:
    tags = OrderedDict((('SomeName', 'some descriptions'),
                        ('SecondName', 'second description')))

    @pytest.fixture()
    def plugin(self):
        def some_decorator(func):
            return func

        instance = ApiSpecPlugin(app=app,
                                 decorators=[some_decorator],
                                 tags=self.tags)
        return instance

    def test__init__(self, plugin):
        assert plugin.app is app
        assert len(plugin.decorators_for_autodoc) == 1
        assert plugin.decorators_for_autodoc[0].__name__ == 'some_decorator'
        spec = plugin.spec
        assert isinstance(spec, APISpec)
        assert (spec.title, spec.version, spec.openapi_version) == (app.name, '1', '2.0')
        assert len(spec.plugins) == 2
        assert isinstance(spec.plugins[0], MarshmallowPlugin)
        assert isinstance(spec.plugins[1], RestfulPlugin)
        assert plugin.spec_tag == {k: {'name': k, 'description': v, 'add_in_spec': True}
                                   for k, v in self.tags.items()}
        assert spec._tags == [{'name': k, 'description': v}
                              for k, v in self.tags.items()]

    def test_after_init_plugin(self):
        mock_self = Mock()
        mock_self._fields = mock_self._converters = []
        ApiSpecPlugin.after_init_plugin(mock_self)
        mock_self._register_doc_blueprint.assert_called_once_with()

    @patch.object(ApiSpecPlugin, '_add_paths_in_spec', autospec=True)
    def test_after_route(self, mock_add_paths_in_spec, plugin):
        tag = 'SomeName'
        url = '/some_resource/<int:id>/'
        plugin.after_route(SomeResourceDetail, 'some_view_name', (url, ), tag=tag)

        schema_name = create_schema_name(SomeResourceDetail.schema)

        assert plugin.spec_schemas[schema_name] == SomeResourceDetail.schema
        assert plugin.spec.components.schemas[schema_name]

        assert plugin.spec_tag[tag]

        mock_add_paths_in_spec.assert_called_once_with(
            plugin,
            path=url, resource=SomeResourceDetail, default_parameters=None, default_schema=None, tag_name=tag
        )

    def test__get_parameters_for_include_models(self):
        result = ApiSpecPlugin._ApiSpecPlugin__get_parameters_for_include_models(SomeResourceDetail)
        assert result == {'default': 'related_model_id',
                          "name": "include",
                          'in': 'query',
                          'format': 'string',
                          "required": False,
                          'description': 'Related relationships to include.\nAvailable:\n`related_model_id`'}

    def test__get_parameters_for_sparse_fieldsets(self):
        description = "List that refers to the name(s) of the fields to be returned `{}`"
        result = ApiSpecPlugin._ApiSpecPlugin__get_parameters_for_sparse_fieldsets(SomeResourceDetail, description)
        assert result == {
            "name": f"fields[{SomeResourceDetail.schema.Meta.type_}]",
            "in": "query",
            "type": "array",
            "required": False,
            "description": description.format(SomeResourceDetail.schema.Meta.type_),
            "items": {"type": "string", "enum": list(SomeResourceDetail.schema._declared_fields.keys())},
        }

    def test__update_parameter_for_field_spec(self):
        new_param = {'foo': 'bar'}
        spec = {'items': {'type': 'some_type', 'enum': [1, 2, 3], 'spam': 'eggs', }}
        ApiSpecPlugin._update_parameter_for_field_spec(new_param, spec)
        assert new_param == {'foo': 'bar', 'items': {'type': 'some_type', 'enum': [1, 2, 3]}}

    def test__get_operations_for_get__list(self, plugin):
        plugin._add_definitions_in_spec(SomeSchema)
        plugin._add_definitions_in_spec(AnotherRelatedModelSchema)
        tag = 'SomeName'
        default_parameter = 'default_parameter'
        result = plugin._get_operations_for_get(SomeResourceList, tag, [default_parameter])
        assert result['tags'] == [tag]
        assert result['produces'] == ['application/json']
        assert result['responses'] == {200: {'description': 'Success'},
                                       404: {'description': 'Not found'}}
        assert result['parameters'][0] == default_parameter
        assert result['parameters'][1] == {
            'default': 'related_model_id', 'name': 'include', 'in': 'query', 'format': 'string', 'required': False,
            'description': 'Related relationships to include.\nAvailable:\n`related_model_id`'
        }
        enum2 = set(result['parameters'][2]['items'].pop('enum'))
        assert enum2 == {'id', 'name', 'type', 'flags', 'description', 'related_model_id'}
        assert result['parameters'][2] == {
            'name': 'fields[some_schema]', 'in': 'query', 'type': 'array', 'required': False,
            'description': 'List that refers to the name(s) of the fields to be returned `some_schema`',
            'items': {'type': 'string'}
        }
        enum3 = set(result['parameters'][3]['items'].pop('enum'))
        assert enum3 == {'id', 'name'}
        assert result['parameters'][3] == {
            'name': 'fields[another_related_model]', 'in': 'query', 'type': 'array', 'required': False,
            'description': 'List that refers to the name(s) of the fields to be returned `another_related_model`',
            'items': {'type': 'string'}
        }
        assert result['parameters'][4:8] == list(plugin._ApiSpecPlugin__list_filters_data)
        assert sorted(result['parameters'][8:], key=lambda i: i['name']) == [
            {'name': 'filter[description]', 'in': 'query', 'type': 'integer', 'required': False,
             'description': 'description attribute filter'},
            {'name': 'filter[flags]', 'in': 'query', 'type': 'integer', 'required': False,
             'description': 'flags attribute filter'},
            {'name': 'filter[id]', 'in': 'query', 'type': 'integer', 'required': False,
             'description': 'id attribute filter'},
            {'name': 'filter[name]', 'in': 'query', 'type': 'string', 'required': False,
             'description': 'name attribute filter'},
            {'name': 'filter[related_model_id.id]', 'in': 'query', 'type': 'integer', 'required': False,
             'description': 'related_model_id.id attribute filter'},
            {'name': 'filter[related_model_id.name]', 'in': 'query', 'type': 'string', 'required': False,
             'description': 'related_model_id.name attribute filter'},
            {'name': 'filter[type]', 'in': 'query', 'type': 'integer', 'required': False,
             'description': 'type attribute filter'},
        ]

    def test__get_operations_for_get__detail(self, plugin):
        plugin._add_definitions_in_spec(SomeSchema)
        plugin._add_definitions_in_spec(AnotherRelatedModelSchema)
        tag = 'SomeName'
        default_parameter = 'default_parameter'
        result = plugin._get_operations_for_get(SomeResourceDetail, tag, [default_parameter])
        assert result['tags'] == [tag]
        assert result['produces'] == ['application/json']
        assert result['responses'] == {200: {'description': 'Success'},
                                       404: {'description': 'Not found'}}
        assert result['parameters'][0] == default_parameter
        assert result['parameters'][1] == plugin.param_id
        assert result['parameters'][2] == {
            'default': 'related_model_id', 'name': 'include', 'in': 'query', 'format': 'string', 'required': False,
            'description': 'Related relationships to include.\nAvailable:\n`related_model_id`'
        }
        enum3 = set(result['parameters'][3]['items'].pop('enum'))
        assert enum3 == {'id', 'name', 'type', 'flags', 'description', 'related_model_id'}
        assert result['parameters'][3] == {
            'name': 'fields[some_schema]', 'in': 'query', 'type': 'array', 'required': False,
            'description': 'List that refers to the name(s) of the fields to be returned `some_schema`',
            'items': {'type': 'string'}
        }
        enum4 = set(result['parameters'][4]['items'].pop('enum'))
        assert enum4 == {'id', 'name'}
        assert result['parameters'][4] == {
            'name': 'fields[another_related_model]', 'in': 'query', 'type': 'array', 'required': False,
            'description': 'List that refers to the name(s) of the fields to be returned `another_related_model`',
            'items': {'type': 'string'}
        }

    def test__get_operations_for_post(self, plugin):
        tag = 'SomeName'
        default_parameter = 'default_parameter'
        schema = SomeSchema
        result = plugin._get_operations_for_post(schema, tag, [default_parameter])
        assert result == {
            'tags': ['SomeName'],
            'produces': ['application/json'],
            'parameters': [
                'default_parameter',
                {'name': 'POST body', 'in': 'body', 'schema': schema, 'required': True,
                 'description': 'SomeName attributes'}
            ],
            'responses': {'201': {'description': 'Created'},
                          '202': {'description': 'Accepted'},
                          '403': {'description': 'This implementation does not accept client-generated IDs'},
                          '404': {'description': 'Not Found'},
                          '409': {'description': 'Conflict'}}
        }

    def test__get_operations_for_patch(self, plugin):
        tag = 'SomeName'
        default_parameter = 'default_parameter'
        schema = SomeSchema
        result = plugin._get_operations_for_patch(schema, tag, [default_parameter])
        assert result == {
            'tags': ['SomeName'],
            'produces': ['application/json'],
            'parameters': [
                'default_parameter',
                {'in': 'path', 'name': 'id', 'required': True, 'type': 'integer', 'format': 'int32'},
                {'name': 'POST body', 'in': 'body', 'schema': schema, 'required': True,
                 'description': 'SomeName attributes'}
            ],
            'responses': {'200': {'description': 'Success'},
                          '201': {'description': 'Created'},
                          '204': {'description': 'No Content'},
                          '403': {'description': 'Forbidden'},
                          '404': {'description': 'Not Found'},
                          '409': {'description': 'Conflict'}}
        }

    def test__get_operations_for_delete(self, plugin):
        tag = 'SomeName'
        default_parameter = 'default_parameter'
        result = plugin._get_operations_for_delete(tag, [default_parameter])
        assert result == {
            'tags': ['SomeName'],
            'produces': ['application/json'],
            'parameters': [
                'default_parameter',
                {'in': 'path', 'name': 'id', 'required': True, 'type': 'integer', 'format': 'int32'}
            ],
            'responses': {'200': {'description': 'Success'},
                          '202': {'description': 'Accepted'},
                          '204': {'description': 'No Content'},
                          '403': {'description': 'Forbidden'},
                          '404': {'description': 'Not Found'}}
        }

    @pytest.fixture()
    def expected_dict_schema(self):
        return lambda resource: {
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
                        "attributes": {"$ref": f"#/definitions/{create_schema_name(resource.schema)}"},
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

    @patch.object(APISpec, 'path')
    @patch.object(ApiSpecPlugin, '_get_operations_for_get', autospec=True)
    @patch.object(ApiSpecPlugin, '_get_operations_for_post', autospec=True)
    @patch.object(ApiSpecPlugin, '_get_operations_for_patch', autospec=True)
    @patch.object(ApiSpecPlugin, '_get_operations_for_delete', autospec=True)
    def test__add_paths_in_spec__detail(self, mock_gof_delete, mock_gof_patch, mock_gof_post, mock_gof_get, 
                                        mock_spec_path, plugin, expected_dict_schema):
        path = '/apispec/some_url'
        tag = 'SomeName'
        schema = expected_dict_schema(SomeResourceDetail)
        default_parameters = ['default_parameter']
        expected_rule = [i for i in plugin.app.url_map._rules if i.rule == path][0]

        plugin._add_paths_in_spec(path, SomeResourceDetail, tag, default_parameters)

        mock_gof_get.assert_called_once_with(plugin, SomeResourceDetail, tag, default_parameters)
        mock_gof_patch.assert_called_once_with(plugin, schema, tag, default_parameters)
        mock_gof_delete.assert_called_once_with(plugin, tag, default_parameters)
        mock_gof_post.assert_not_called()

        mock_spec_path.assert_called_once_with(
            path=path,
            operations={'get': mock_gof_get.return_value,
                        'patch': mock_gof_patch.return_value,
                        'delete': mock_gof_delete.return_value},
            rule=expected_rule,
            resource=SomeResourceDetail
        )

    @patch.object(APISpec, 'path')
    @patch.object(ApiSpecPlugin, '_get_operations_for_get', autospec=True)
    @patch.object(ApiSpecPlugin, '_get_operations_for_post', autospec=True)
    @patch.object(ApiSpecPlugin, '_get_operations_for_patch', autospec=True)
    @patch.object(ApiSpecPlugin, '_get_operations_for_delete', autospec=True)
    def test__add_paths_in_spec__list(self, mock_gof_delete, mock_gof_patch, mock_gof_post, mock_gof_get,
                                      mock_spec_path, plugin, expected_dict_schema):
        path = '/apispec/some_url'
        tag = 'SomeName'
        schema = expected_dict_schema(SomeResourceList)
        default_parameters = ['default_parameter']
        expected_rule = [i for i in plugin.app.url_map._rules if i.rule == path][0]

        plugin._add_paths_in_spec(path, SomeResourceList, tag, default_parameters)

        mock_gof_get.assert_called_once_with(plugin, SomeResourceList, tag, default_parameters)
        mock_gof_post.assert_called_once_with(plugin, schema, tag, default_parameters)
        mock_gof_delete.assert_not_called()
        mock_gof_patch.assert_not_called()

        mock_spec_path.assert_called_once_with(
            path=path,
            operations={'get': mock_gof_get.return_value,
                        'post': mock_gof_post.return_value},
            rule=expected_rule,
            resource=SomeResourceList
        )

    @pytest.mark.parametrize('apispec_version_major, func_to_call', (
            (0, 'add_tag'),
            (1, 'tag'),
            (2, 'tag'),
    ))
    def test__add_tags_in_spec(self, apispec_version_major, func_to_call):
        tag = {'name': 'tag_name', 'description': 'tag_description', 'add_in_spec': True}
        mock_self = Mock()
        mock_self.spec_tag = {tag['name']: tag}
        with patch(f'{module_path}.APISPEC_VERSION_MAJOR', new=apispec_version_major):
            ApiSpecPlugin._add_tags_in_spec(mock_self, tag)

            # do nothing if already added in spec
            getattr(mock_self.spec, func_to_call).assert_not_called()
            assert mock_self.spec_tag[tag['name']]['add_in_spec'] is True

            # else add and mark
            tag['add_in_spec'] = False
            ApiSpecPlugin._add_tags_in_spec(mock_self, tag)
            getattr(mock_self.spec, func_to_call).assert_called_once_with({"name": tag["name"], "description": tag["description"]})
            assert mock_self.spec_tag[tag['name']]['add_in_spec'] is True


def test_resolve_nested_schema():
    mock_self = Mock()
    mock_self.refs = []
    mock_self.spec.components.schemas = {}

    schema = SomeSchema()

    result = resolve_nested_schema(mock_self, schema)

    assert result is mock_self.get_ref_dict.return_value
    mock_self.get_ref_dict.assert_called_once_with(schema)
    mock_self.spec.components.schema.assert_called_once_with(create_schema_name(schema),
                                                             schema=schema)


def test_resolve_nested_schema__schema_name_in_spec():
    schema = SomeSchema()
    name = create_schema_name(schema)
    mock_self = Mock()
    mock_self.refs = []
    mock_self.spec.components.schemas = {name: SomeSchema}

    result = resolve_nested_schema(mock_self, schema)

    assert result is mock_self.get_ref_dict.return_value
    mock_self.get_ref_dict.assert_called_once_with(schema)
    mock_self.spec.components.schema.assert_not_called()
