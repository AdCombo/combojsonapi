from unittest.mock import Mock

import pytest
from flask_rest_jsonapi.utils import SPLIT_REL
from marshmallow import Schema, fields

from combojsonapi.postgresql_jsonb import PostgreSqlJSONB
from combojsonapi.postgresql_jsonb.schema import SchemaJSONB


@pytest.fixture
def plugin():
    return PostgreSqlJSONB()


@pytest.fixture
def schema():
    class TestSchema(SchemaJSONB):
        name = fields.Integer()

    class ParentSchema(Schema):
        test_schema = fields.Nested('TestSchema')

    return ParentSchema


class TestPostgreSqlJSONB:
    def test_before_data_layers_sorting_alchemy_nested_resolve(self, plugin, schema):
        mock_self_nested = Mock()
        mock_self_nested.sort_ = {'field': f'test_schema{SPLIT_REL}name', 'order': 'asc'}
        mock_self_nested.name = 'test_schema'
        mock_self_nested.schema = schema
        plugin._create_sort = Mock()
        plugin._create_sort.return_value = True

        res = plugin.before_data_layers_sorting_alchemy_nested_resolve(mock_self_nested)

        assert res == (True, [],)
