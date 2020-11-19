from typing import List, Optional
from unittest import mock
from unittest.mock import Mock, MagicMock

import pytest
from flask_combo_jsonapi.exceptions import InvalidFilters
from flask_combo_jsonapi.utils import SPLIT_REL
from marshmallow import Schema, fields

from combojsonapi.postgresql_jsonb import PostgreSqlJSONB, is_seq_collection
from combojsonapi.postgresql_jsonb.schema import SchemaJSONB
from combojsonapi.utils import Relationship


@pytest.mark.parametrize('value, result', (
        ([], True),
        (set(), True),
        (tuple(), True),
        ({}, False),
        (123, False),
        ('123', False),
))
def test_is_seq_collection(value, result):
    assert is_seq_collection(value) is result


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
        name._desc_sql_sort_ = assert_custom_sort

    class RelatedSchema(Schema):
        jsonb_field = fields.Nested('TestSchema')
        string_field = fields.String()

    class ParentSchema(Schema):
        test_schema = fields.Nested('TestSchema')
        string_field = fields.String()
        related_schema = Relationship(nested='RelatedSchema', schema='RelatedSchema')

    return ParentSchema


def assert_custom_opertor(marshmallow_field, model_column, value, operator):
    assert operator == '__ilike__'
    return True


def assert_custom_sort(marshmallow_field, model_column):
    return True


class TestPostgreSqlJSONB:
    @pytest.fixture()
    def mock_self_nested(self, schema):
        mock_self_nested = MagicMock()
        mock_self_nested.schema = schema
        mock_self_nested.name = 'test_schema'
        mock_self_nested.value = 123
        mock_self_nested.operator = '__eq__'
        mock_self_nested.filter_ = {'name': 'test_schema.name', 'op': 'eq'}
        mock_self_nested.sort_ = {'field': ''}
        return mock_self_nested

    @pytest.fixture()
    def mock__create_filter(self):
        with mock.patch.object(PostgreSqlJSONB, '_create_filter') as mocked:
            yield mocked

    @pytest.mark.parametrize('field', (fields.Email(), fields.Dict(), fields.Decimal(), fields.Url()))
    def test_get_property_type__without_schema(self, plugin, field):
        assert plugin.get_property_type(field) is plugin.mapping_ma_field_to_type[type(field)]

    def test_get_property_type__with_schema(self, plugin):
        class FakeType(dict):
            pass

        class SomeClass:
            pass

        mock_schema = mock.Mock()
        mock_schema.TYPE_MAPPING = {FakeType: SomeClass}
        assert plugin.get_property_type(SomeClass(), mock_schema) is FakeType

    def test_add_mapping_field_to_python_type(self, plugin):
        class FakeType(dict):
            pass

        plugin.add_mapping_field_to_python_type(fields.String, FakeType)
        assert plugin.mapping_ma_field_to_type[fields.String] is FakeType

    def test_before_data_layers_sorting_alchemy_nested_resolve(self, plugin, schema):
        mock_self_nested = Mock()
        mock_self_nested.sort_ = {'field': f'test_schema{SPLIT_REL}name', 'order': 'asc'}
        mock_self_nested.name = 'test_schema'
        mock_self_nested.schema = schema
        plugin._create_sort = Mock()
        plugin._create_sort.return_value = True

        res = plugin.before_data_layers_sorting_alchemy_nested_resolve(mock_self_nested)

        assert res == (True, [],)

    def test_before_data_layers_filtering_alchemy_nested_resolve(self, plugin, mock_self_nested, mock__create_filter):
        mock__create_filter.return_value = 'filter', 'joins'
        result = plugin.before_data_layers_filtering_alchemy_nested_resolve(mock_self_nested)
        assert result == mock__create_filter.return_value
        mock__create_filter.assert_called_once_with(
            mock_self_nested, marshmallow_field=mock_self_nested.schema._declared_fields[mock_self_nested.name],
            model_column=mock_self_nested.column, operator=mock_self_nested.filter_['op'], value=mock_self_nested.value
        )

    def test_before_data_layers_filtering_alchemy_nested_resolve__not_splitted_name(self, plugin, mock_self_nested,
                                                                                    mock__create_filter):
        mock_self_nested.filter_['name'] = 'not_splitted_name'
        result = plugin.before_data_layers_filtering_alchemy_nested_resolve(mock_self_nested)
        assert result is None
        mock__create_filter.assert_not_called()

    @pytest.mark.parametrize('filter_', ('or', 'and', 'not'))
    def test_before_data_layers_filtering_alchemy_nested_resolve__or_and_not_filters(self, plugin, mock_self_nested,
                                                                                     mock__create_filter, filter_):
        mock_self_nested.filter_[filter_] = ''
        result = plugin.before_data_layers_filtering_alchemy_nested_resolve(mock_self_nested)
        assert result is None
        mock__create_filter.assert_not_called()

    @pytest.mark.parametrize('filter_name, result', (
            pytest.param('test_schema.lvl1', True, id='jsonb field'),
            pytest.param('string_field', False, id='not jsonb field'),
            pytest.param('related_schema.jsonb_field.name', True, id='jsonb field of related schema'),
            pytest.param('related_schema.string_field', False, id='not jsonb field of related schema'),
    ))
    def test__isinstance_jsonb(self, schema, filter_name, result):
        assert PostgreSqlJSONB._isinstance_jsonb(schema, filter_name) is result

    @pytest.mark.parametrize('filter_name', (
        'test_schema', 'related_schema.jsonb_field'
    ))
    def test__isinstance__invalid_filters(self, schema, filter_name):
        with pytest.raises(InvalidFilters) as e:
            PostgreSqlJSONB._isinstance_jsonb(schema, filter_name)
        assert e.value.detail == f'Invalid JSONB filter: {filter_name}'

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
            order='asc')

        mock_model_column.op("->").assert_called_once()

    def test__create_sort_with_custom_sort(self, plugin, schema):
        mock_self_nested = Mock()
        mock_self_nested.sort_ = {'field': f'test_schema{SPLIT_REL}lvl1{SPLIT_REL}name', 'order': 'desc'}
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
        assert res is True

    def test_create_sort__not_jsonb_field(self, plugin, schema, mock_self_nested):
        with pytest.raises(InvalidFilters):
            plugin._create_sort(
                self_nested=mock_self_nested,
                marshmallow_field=schema._declared_fields['string_field'],
                model_column=Mock(),
                order='desc'
            )

    def test_create_sort__wrong_fields_path(self, plugin, schema, mock_self_nested):
        mock_self_nested.sort_ = {'field': 'spam.eggs'}
        with pytest.raises(InvalidFilters):
            plugin._create_sort(
                self_nested=mock_self_nested,
                marshmallow_field=schema._declared_fields['test_schema'],
                model_column=Mock(),
                order='desc'
            )

    def test_create_sort__through_related_schema(self, schema, mock_self_nested):
        mock_self_nested.sort_['field'] = 'related_schema.jsonb_field.name'
        mock_self = Mock()
        mock_model_column = Mock()

        result = PostgreSqlJSONB._create_sort(
            mock_self,
            self_nested=mock_self_nested,
            marshmallow_field=schema._declared_fields['related_schema'],
            model_column=mock_model_column,
            order='asc'
        )
        assert result == mock_self._create_sort.return_value
        # check that func was called recursively
        mock_self._create_sort.assert_called_once_with(
            mock_self_nested, schema._declared_fields['related_schema'].schema._declared_fields['jsonb_field'],
            mock_model_column.mapper.class_.jsonb_field, 'asc'
        )

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

    def test_create_filter__not_jsonb_field(self, plugin, schema, mock_self_nested):
        with pytest.raises(InvalidFilters):
            plugin._create_filter(
                self_nested=mock_self_nested,
                marshmallow_field=schema._declared_fields['string_field'],
                model_column=Mock(),
                operator=mock_self_nested.operator,
                value=mock_self_nested.value
            )

    def test_create_filter__wrong_field_path(self, plugin, schema, mock_self_nested):
        mock_self_nested.filter_['name'] = 'spam.eggs'
        with pytest.raises(InvalidFilters):
            plugin._create_filter(
                self_nested=mock_self_nested,
                marshmallow_field=schema._declared_fields['test_schema'],
                model_column=Mock(),
                operator=mock_self_nested.operator,
                value=mock_self_nested.value
            )

    def test_create_filter__through_related_schema(self, schema, mock_self_nested):
        mock_self_nested.filter_['name'] = 'related_schema.jsonb_field.name'
        mock_self = Mock()
        mock_self._create_filter.return_value = 'filter', []
        mock_model_column = Mock()

        result = PostgreSqlJSONB._create_filter(
            mock_self,
            self_nested=mock_self_nested,
            marshmallow_field=schema._declared_fields['related_schema'],
            model_column=mock_model_column,
            operator=mock_self_nested.operator,
            value=mock_self_nested.value
        )
        assert result[0] == mock_self._create_filter.return_value[0]
        assert result[1] == mock_self._create_filter.return_value[1] + [[mock_model_column]]
        # check that func was called recursively
        mock_self._create_filter.assert_called_once_with(
            mock_self_nested, schema._declared_fields['related_schema'].schema._declared_fields['jsonb_field'],
            mock_model_column.mapper.class_.jsonb_field, mock_self_nested.operator, mock_self_nested.value
        )
