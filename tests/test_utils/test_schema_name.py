from unittest.mock import patch

import pytest

from combojsonapi.utils import create_schema_name
from combojsonapi.utils.schema_name import NO_ARGS_ERROR, INVALID_SCHEMA_TYPE, NO_SCHEMA_FOUND_ERROR
from tests.test_utils import SimpleSchema

module_path = 'combojsonapi.utils.schema_name'


class TestCreateSchemaName:

    def test_no_args(self):
        with pytest.raises(ValueError) as e:
            create_schema_name()
        assert e.value.args[0] == NO_ARGS_ERROR

    def test_invalid_schema_type(self):
        with pytest.raises(TypeError) as e:
            create_schema_name(schema=int)
        assert e.value.args[0] == INVALID_SCHEMA_TYPE

    def test_no_schema_name_in_class_registry(self):
        schema_name = "FakeSchema"
        with pytest.raises(ValueError) as e:
            create_schema_name(name_schema=schema_name)
        assert e.value.args[0] == NO_SCHEMA_FOUND_ERROR.format(schema_name=schema_name)

    @pytest.mark.parametrize('resolver, modifiers, expected_result_from_name, expected_result_from_schema', (
            (lambda x: x.__name__, [], 'SimpleSchema', 'SimpleSchema'),
            (lambda x: x.__name__[:-6], [], 'Simple', 'Simple'),
            (lambda x: x.__name__, ['only', 'exclude'], 'SimpleSchema',
             'SimpleSchema(only={\'id\'},exclude={\'name\'})'),
            (lambda x: x.__name__[:-6], ['only', 'exclude'], 'Simple', 'Simple(only={\'id\'},exclude={\'name\'})'),
    ))
    def test(self, resolver, modifiers, expected_result_from_name, expected_result_from_schema):
        schema = SimpleSchema(only=['id'], exclude=['name'])
        with patch(f'{module_path}.MODIFIERS', new=modifiers):
            with patch(f'{module_path}.resolver', side_effect=resolver) as mock_resolver:
                result_from_name = create_schema_name(name_schema=SimpleSchema.__name__)
                result_from_schema = create_schema_name(schema=schema)
                assert result_from_name == expected_result_from_name
                assert result_from_schema == expected_result_from_schema


