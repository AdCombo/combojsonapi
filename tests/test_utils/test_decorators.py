from unittest.mock import Mock

import pytest

from combojsonapi.utils import get_decorators_for_resource


@pytest.mark.parametrize('res_decorators, api_decorators, disable_global_decorators, expected_result', (
    pytest.param(['res_dec'], ['api_dec'], False, ['res_dec', 'api_dec'], id='res + api decorators'),
    pytest.param(['res_dec'], ['api_dec'], True, ['res_dec'], id='res decorators only'),
    pytest.param([], ['api_dec'], False, ['api_dec'], id='api decorators only'),
))
def test_get_decorators_for_resource(res_decorators, api_decorators, disable_global_decorators, expected_result):
    resource = Mock()
    resource.decorators = res_decorators
    if disable_global_decorators is not None:
        resource.disable_global_decorators = disable_global_decorators
    self_json_api = Mock()
    self_json_api.decorators = api_decorators
    result = get_decorators_for_resource(resource, self_json_api)
    assert result == expected_result

