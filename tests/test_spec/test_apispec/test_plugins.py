from unittest.mock import patch, Mock

import pytest
from apispec import BasePlugin
from apispec.exceptions import PluginMethodNotImplementedError
from werkzeug.routing import IntegerConverter, UnicodeConverter

from combojsonapi.spec.apispec import FlaskPlugin


class TestFlaskPlugin:
    @pytest.fixture()
    def plugin(self):
        return FlaskPlugin()

    @pytest.fixture()
    def mock_rule(self):
        rule = Mock()
        rule.arguments = ['foo', 'bar']
        rule._converters = {'foo': IntegerConverter(None), 'bar': UnicodeConverter(None)}
        rule.rule = '/rule_path'
        return rule

    @patch.object(BasePlugin, 'init_spec')
    def test_init_spec(self, mock_super_init_spec, plugin):
        mock_spec = Mock()
        plugin.init_spec(mock_spec)
        mock_super_init_spec.assert_called_once_with(mock_spec)
        assert plugin.openapi_version is mock_spec.openapi_version

    @pytest.mark.parametrize('flask_path, open_api_path', (
            ('/api/foo/<int:bar>/', '/api/foo/{bar}/'),
            ('/spam/<string:eggs>/', '/spam/{eggs}/'),
            ('/foo/<int:id>/<string:bar>/', '/foo/{id}/{bar}/')
    ))
    def test_flaskpath2openapi(self, flask_path, open_api_path):
        assert FlaskPlugin.flaskpath2openapi(flask_path) == open_api_path

    def test_register_converter(self, plugin):
        converter = Mock()
        type_ = Mock()
        conv_format = Mock()
        plugin.register_converter(converter, type_, conv_format)
        assert plugin.converter_mapping[converter] == (type_, conv_format)

    @pytest.mark.parametrize('version, expected_result', (
            (1, [{'in': 'path', 'name': 'foo', 'required': True, 'type': 'integer', 'format': 'int32'},
                 {'in': 'path', 'name': 'bar', 'required': True, 'type': 'string'}]),
            (3, [{'in': 'path', 'name': 'foo', 'required': True, 'schema': {'type': 'integer', 'format': 'int32'}},
                 {'in': 'path', 'name': 'bar', 'required': True, 'schema': {'type': 'string'}}])
    ))
    def test_rule_to_params(self, plugin, mock_rule, version, expected_result):
        openapi_version = Mock()
        openapi_version.major = version
        plugin.openapi_version = openapi_version

        result = plugin.rule_to_params(mock_rule)
        assert result == expected_result

    def test_path_helper__no_rule(self, plugin):
        with pytest.raises(PluginMethodNotImplementedError):
            plugin.path_helper(None)

    def test_path_helper(self, plugin, mock_rule):
        operations = {
            'get': {
                'parameters': [
                    {'in': 'path', 'name': 'foo', 'description': 'foo field'}
                ]
            }
        }
        openapi_version = Mock()
        openapi_version.major = 2
        plugin.openapi_version = openapi_version

        result = plugin.path_helper(mock_rule, operations)
        assert result == mock_rule.rule

        assert operations == {
            'get': {
                'parameters': [
                    {'in': 'path', 'name': 'foo', 'description': 'foo field', 'required': True, 'type': 'integer',
                     'format': 'int32'},
                    {'in': 'path', 'name': 'bar', 'required': True, 'type': 'string'}
                ]
            }
        }

