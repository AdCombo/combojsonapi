from typing import List, Optional
from unittest import mock
from unittest.mock import Mock

import pytest
from flask_combo_jsonapi.utils import SPLIT_REL
from marshmallow import Schema, fields

from combojsonapi.postgresql_jsonb import PostgreSqlJSONB
from combojsonapi.postgresql_jsonb.schema import SchemaJSONB


@pytest.fixture
def plugin():
    return PostgreSqlJSONB()


@pytest.fixture
def custom_field():
    class CustomEnumField(fields.Integer):

        def __init__(self, *args, default: int = 0, allowed_values: Optional[List[int]] = None, **kwargs):
            self.default = default
            self.allowed_values = allowed_values or []
            super().__init__(*args, enum=[1, 2, 3, 4], **kwargs)

        def _deserialize(self, value, attr, data, **kwargs):
            try:
                value = int(value)
                value = value if value in self.allowed_values else self.default
            except TypeError as e:
                value = self.default
            return value

    return CustomEnumField


@pytest.fixture
def schema(custom_field):

    class TestSchema(SchemaJSONB):
        name = fields.Integer()
        lvl1 = fields.Nested('TestSchemaLvl2')
        type_test = custom_field(allowed_values=[1, 2, 3, 5, 8])

    class TestSchemaLvl2(SchemaJSONB):
        name = fields.String()
        list = fields.List(fields.String())
        list._ilike_sql_filter_ = assert_custom_opertor
        name._desc_sql_filter_ = assert_custom_sort

    class ParentSchema(Schema):
        test_schema = fields.Nested('TestSchema')

    return ParentSchema


def assert_custom_opertor(marshmallow_field, model_column, value, operator):
    assert operator == '__ilike__'
    return True


def assert_custom_sort(marshmallow_field, model_column):
    return True


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

    @mock.patch('combojsonapi.postgresql_jsonb.plugin.cast', autospec=True)
    def test_custom_mapping(self, mock_cast, plugin, schema, custom_field):
        mock_self_nested = Mock()
        mock_operator = 'eq'
        mock_value = 1
        mock_self_nested.filter_ = {
            'name': f'test_schema{SPLIT_REL}type_test',
            'op': mock_operator,
            'val': mock_value,
        }
        mock_self_nested.schema = schema()
        mock_self_nested.operator = mock_operator
        mock_marshmallow_field = schema().fields['test_schema']
        mock_model_column = Mock()
        plugin.add_mapping_field_to_python_type(custom_field, int)
        mock_cast.eq = Mock(return_value=True)

        assert True, [] == plugin._create_filter(
            self_nested=mock_self_nested,
            marshmallow_field=mock_marshmallow_field,
            model_column=mock_model_column,
            operator=mock_operator,
            value=mock_value
        )

    def test__create_sort(self, plugin, schema):
        mock_self_nested = Mock()
        mock_self_nested.sort_ = {'field': f'test_schema{SPLIT_REL}lvl1{SPLIT_REL}name', 'order': 'asc'}
        mock_self_nested.name = 'test_schema'
        mock_self_nested.schema = schema
        mock_marshmallow_field = schema().fields['test_schema']
        mock_model_column = Mock()

        plugin._create_sort(
            self_nested=mock_self_nested,
            marshmallow_field=mock_marshmallow_field,
            model_column=mock_model_column,
            order='desc')

        mock_model_column.op("->").assert_called_once()

    def test__create_sort_with_custom_sort(self, plugin, schema):
        mock_self_nested = Mock()
        mock_self_nested.sort_ = {'field': f'test_schema{SPLIT_REL}lvl1{SPLIT_REL}name', 'order': 'decs'}
        mock_self_nested.name = 'test_schema'
        mock_self_nested.schema = schema
        mock_marshmallow_field = schema().fields['test_schema']
        mock_model_column = Mock()

        res = plugin._create_sort(
            self_nested=mock_self_nested,
            marshmallow_field=mock_marshmallow_field,
            model_column=mock_model_column,
            order='desc')

        mock_model_column.op("->").assert_called_once()
        assert res == True

    def test__create_filter(self, plugin, schema):
        mock_operator = 'eq'
        mock_value = 'string'
        mock_self_nested = Mock()
        mock_self_nested.filter_ = {
            'name': f'test_schema{SPLIT_REL}lvl1{SPLIT_REL}name',
            'op': mock_operator,
            'val': mock_value,
        }
        mock_self_nested.operator = '__eq__'
        mock_self_nested.name = 'test_schema'
        mock_self_nested.name = 'test_schema'

        mock_self_nested.schema = schema
        mock_marshmallow_field = schema().fields['test_schema']
        mock_model_column = Mock()


        plugin._create_filter(
            self_nested=mock_self_nested,
            marshmallow_field=mock_marshmallow_field,
            model_column=mock_model_column,
            operator=mock_operator,
            value=mock_value)

        mock_model_column.op("->").assert_called_once()

    def test__create_filter_with_custom_op(self, plugin, schema):
        mock_operator = 'ilike'
        mock_value = 'string'
        mock_self_nested = Mock()
        mock_self_nested.filter_ = {
            'name': f'test_schema{SPLIT_REL}lvl1{SPLIT_REL}list',
            'op': mock_operator,
            'val': mock_value,
        }
        mock_self_nested.operator = '__ilike__'
        mock_self_nested.name = 'test_schema'

        mock_self_nested.schema = schema
        mock_marshmallow_field = schema().fields['test_schema']
        mock_model_column = Mock()

        plugin._create_filter(
            self_nested=mock_self_nested,
            marshmallow_field=mock_marshmallow_field,
            model_column=mock_model_column,
            operator=mock_operator,
            value=mock_value)

        mock_model_column.op("->").assert_called_once()
