from collections import OrderedDict
from unittest.mock import Mock, patch

import pytest
from apispec import BasePlugin, APISpec

from combojsonapi.spec.apispec import MarshmallowPlugin
from combojsonapi.spec.plugins_for_apispec import flaskpath2swagger, RestfulPlugin
from combojsonapi.utils import create_schema_name
from tests.test_spec import SomeSchema, app


@pytest.mark.parametrize('flask_path, open_api_path', (
        ('/api/foo/<int:bar>/', '/api/foo/{bar}/'),
        ('/spam/<string:eggs>/', '/spam/{eggs}/'),
        ('/foo/<int:id>/<string:bar>/', '/foo/{id}/{bar}/')
))
def test_flaskpath2swagger(flask_path, open_api_path):
    assert flaskpath2swagger(flask_path) == open_api_path


class TestRestfulPlugin:
    @pytest.fixture()
    def spec(self, plugin):
        return APISpec(app.name,
                       app.config.get("API_VERSION", "1"),
                       app.config.get("OPENAPI_VERSION", "2.0"),
                       plugins=[plugin, MarshmallowPlugin()])

    @pytest.fixture()
    def plugin(self):
        return RestfulPlugin()

    @patch.object(BasePlugin, 'init_spec')
    def test_init_spec(self, mock_super_init_spec, plugin):
        mock_spec = Mock()
        plugin.init_spec(mock_spec)
        mock_super_init_spec.assert_called_once_with(mock_spec)
        assert plugin.spec is mock_spec

    def test__ref_to_spec__list_data(self):
        mock_self = Mock()
        data = [1, 2, 'foo', 'bar']
        RestfulPlugin._ref_to_spec(mock_self, data)
        assert mock_self._ref_to_spec.call_count == len(data)
        for i, (args, _) in enumerate(mock_self._ref_to_spec.call_args_list):
            assert args == (data[i], )

    def test__ref_to_spec__dict_with_list_values_data(self):
        mock_self = Mock()
        data = [1, 2, 'foo', 'bar']
        data_dict = OrderedDict([('spam', data[:2]), ('eggs', data[2:])])
        RestfulPlugin._ref_to_spec(mock_self, data_dict)
        assert mock_self._ref_to_spec.call_count == len(data)
        for i, (args, _) in enumerate(mock_self._ref_to_spec.call_args_list):
            assert args == (data[i], )

    def test__ref_to_spec__nested_dicts_data(self):
        mock_self = Mock()
        data = OrderedDict([('foo', {'bar': 1}), ('spam', {'eggs': 1})])
        RestfulPlugin._ref_to_spec(mock_self, data)
        assert mock_self._ref_to_spec.call_count == len(data)
        for i, (values) in enumerate(data.values()):
            assert mock_self._ref_to_spec.call_args_list[i][0] == (values, )

    def test__ref_to_spec__with_ref_data(self):
        mock_self = Mock()
        mock_self.spec.components.schemas = {}
        schema = SomeSchema
        schema_name = create_schema_name(schema)
        data = {'$ref': f'#/definitions/{schema.__name__}'}
        RestfulPlugin._ref_to_spec(mock_self, data)
        mock_self.spec.components.schema.assert_called_once_with(schema_name, schema=schema)
        assert data['$ref'] == f'#/definitions/{schema_name}'

    def test_operation_helper(self, plugin, spec):
        plugin.init_spec(spec)
        mock_resource = Mock()
        mock_resource.methods = ['GET', 'POST']
        mock_resource.get.__doc__ = """
        ---
        summary: Some summary
        tags:
          - SomeName
        parameters:
        - in: query
          schema:
            $ref: '#/definitions/SchemaReversedName'
        consumes:
        - application/json
        responses:
          200:
            description: Success
          400:
            description: Error
          500:
            description: Server error
        """
        operations = {}
        plugin.operation_helper(operations=operations, resource=mock_resource)
        assert sorted(operations['get'].pop('parameters'), key=lambda d: d['name']) == [
            {'name': 'array_field', 'in': 'query', 'type': 'array', 'items': {'type': 'integer'},
             'description': 'just array field with integers'},
            {'name': 'id', 'in': 'query', 'type': 'integer', 'description': 'just id field'},
            {'name': 'name', 'in': 'query', 'type': 'string', 'description': 'just name field'},
        ]
        assert operations == {
            'get': {
                'summary': 'Some summary',
                'tags': ['SomeName'],
                'consumes': ['application/json'],
                'responses': {
                    200: {'description': 'Success'},
                    400: {'description': 'Error'},
                    500: {'description': 'Server error'}
                }
            }
        }
