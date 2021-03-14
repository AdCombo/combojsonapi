from unittest.mock import Mock, patch

import pytest
from flask import Blueprint, Flask

from combojsonapi.spec.apispec import _add_leading_slash, DocBlueprintMixin


module_path = 'combojsonapi.spec.apispec'


@pytest.mark.parametrize('input_', ('/some_string', 'some_string'))
def test_leading_slash(input_):
    assert _add_leading_slash(input_) == '/some_string'


class TestDocBlueprintMixin:
    @classmethod
    def some_dec(cls, func):
        return {'decorated': func}

    @patch.object(Blueprint, 'add_url_rule', autospec=True)
    def test__register_doc_blueprint(self, mock_add_url_rule):
        url = '/api/swagger'
        mock_self = Mock()
        mock_self._app.config = {'OPENAPI_URL_PREFIX': url}
        mock_self.decorators_for_autodoc = [self.some_dec]
        DocBlueprintMixin._register_doc_blueprint(mock_self)

        blueprint = mock_self._register_redoc_rule.call_args[0][0]
        assert blueprint.template_folder == './templates'
        assert blueprint.url_prefix == url
        mock_add_url_rule.assert_called_once_with(blueprint, '/openapi.json', endpoint='openapi_json',
                                                  view_func=self.some_dec(mock_self._openapi_json))

        mock_self._register_redoc_rule.assert_called_once_with(blueprint)
        mock_self._register_swagger_ui_rule.assert_called_once_with(blueprint)
        mock_self._app.register_blueprint.assert_called_once_with(blueprint)

    def test__register_doc_blueprint__no_openapi_url_prefix(self):
        mock_self = Mock()
        mock_self._app.config = {'OPENAPI_URL_PREFIX': None}
        DocBlueprintMixin._register_doc_blueprint(mock_self)

        mock_self._register_redoc_rule.assert_not_called()
        mock_self._register_swagger_ui_rule.assert_not_called()
        mock_self._app.register_blueprint.assert_not_called()

    @pytest.mark.parametrize('redoc_url, redoc_version, expected_redoc_url', (
            pytest.param('custom_redoc_url', None, 'custom_redoc_url', id='custom url'),
            pytest.param(None, 'latest', 'https://rebilly.github.io/ReDoc/releases/latest/redoc.min.js',
                         id='no url, latest v'),
            pytest.param(None, '', 'https://rebilly.github.io/ReDoc/releases/latest/redoc.min.js',
                         id='no url, latest v by default'),
            pytest.param(None, 'v1.5', 'https://rebilly.github.io/ReDoc/releases/v1.5/redoc.min.js',
                         id='no url, v1.5'),
            pytest.param(None, 'next', 'https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js',
                         id='no url, next v'),
            pytest.param(None, 'v2.3', 'https://cdn.jsdelivr.net/npm/redoc@v2.3/bundles/redoc.standalone.js',
                         id='no url, v2.3'),
    ))
    def test__register_redoc_rule(self, redoc_url, redoc_version, expected_redoc_url):
        redoc_path = '/api/redoc'
        mock_self = Mock()
        mock_self._app.config = {'OPENAPI_REDOC_PATH': redoc_path,
                                 'OPENAPI_REDOC_URL': redoc_url}
        if redoc_version:
            mock_self._app.config['OPENAPI_REDOC_VERSION'] = redoc_version

        mock_self.decorators_for_autodoc = [self.some_dec]
        mock_blueprint = Mock()

        DocBlueprintMixin._register_redoc_rule(mock_self, mock_blueprint)

        assert mock_self._redoc_url == expected_redoc_url
        mock_blueprint.add_url_rule.assert_called_once_with(redoc_path, endpoint='openapi_redoc',
                                                            view_func=self.some_dec(mock_self._openapi_redoc))

    def test__register_redoc_rule__no_redoc_path(self):
        mock_self = Mock()
        mock_self._app.config = {'OPENAPI_REDOC_PATH': None}
        mock_blueprint = Mock()

        DocBlueprintMixin._register_redoc_rule(mock_self, mock_blueprint)
        assert isinstance(mock_self._redoc_url, Mock)
        mock_blueprint.add_url_rule.assert_not_called()

    @pytest.mark.parametrize('swagger_ui_url, swagger_ui_version, expected_result_url', (
            pytest.param('custom_swagger_ui_url', None, 'custom_swagger_ui_url', id='custom url'),
            pytest.param(None, 'latest', 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/latest/',
                         id='url with latest v'),
            pytest.param(None, 'v.1.10', 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/v1.10/',
                         id='url with v1.10'),
    ))
    def test_register_swagger_ui_rule(self, swagger_ui_url, swagger_ui_version, expected_result_url):
        mock_self = Mock()
        mock_self.decorators_for_autodoc = [self.some_dec]
        mock_self._app.config = {'OPENAPI_SWAGGER_UI_PATH': '/swagger_ui',
                                 'OPENAPI_SWAGGER_UI_URL': swagger_ui_url,
                                 'OPENAPI_SWAGGER_UI_VERSION': swagger_ui_version}
        mock_blueprint = Mock()

        DocBlueprintMixin._register_swagger_ui_rule(mock_self, mock_blueprint)
        mock_self._swagger_ui_url = expected_result_url
        mock_self._swagger_ui_supported_submit_methods = ["get", "put", "post", "delete",
                                                          "options", "head", "patch", "trace"]
        mock_blueprint.add_url_rule.assert_called_once_with('/swagger_ui', endpoint='openapi_swagger_ui',
                                                            view_func=self.some_dec(mock_self._openapi_swagger_ui))

    def test_register_swagger_ui_rule__no_path(self):
        mock_self = Mock()
        mock_self._app.config = {'OPENAPI_SWAGGER_UI_PATH': None}
        mock_blueprint = Mock()

        DocBlueprintMixin._register_swagger_ui_rule(mock_self, mock_blueprint)
        assert isinstance(mock_self._swagger_ui_rule, Mock)
        assert isinstance(mock_self._swagger_ui_supported_submit_methods, Mock)
        mock_blueprint.add_url_rule.assert_not_called()

    @patch(f'{module_path}.json.dumps', autospec=True)
    @patch(f'{module_path}.current_app', spec=Flask)  # https://github.com/pallets/flask/issues/3637
    def test__openapi_json(self, mock_current_app, mock_dumps):
        mock_self = Mock()
        DocBlueprintMixin._openapi_json(mock_self)
        mock_current_app.response_class.assert_called_once_with(mock_dumps.return_value, mimetype="application/json")
        mock_dumps.assert_called_once_with(mock_self.spec.to_dict.return_value, indent=2)

    @patch(f'{module_path}.flask.render_template', autospec=True)
    def test__openapi_redoc(self, mock_render_template):
        mock_self = Mock()
        DocBlueprintMixin._openapi_redoc(mock_self)
        mock_render_template.assert_called_once_with('redoc.html', title=mock_self._app.name,
                                                     redoc_url=mock_self._redoc_url)

    @patch(f'{module_path}.flask.render_template', autospec=True)
    def test__openapi_swagger_ui(self, mock_render_template):
        mock_self = Mock()
        DocBlueprintMixin._openapi_swagger_ui(mock_self)
        mock_render_template.assert_called_once_with(
            'swagger_ui.html', title=mock_self._app.name, swagger_ui_url=mock_self._swagger_ui_url,
            swagger_ui_supported_submit_methods=mock_self._swagger_ui_supported_submit_methods
        )
