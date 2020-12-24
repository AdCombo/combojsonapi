import datetime
from decimal import Decimal
from typing import Any, Optional, Union, Dict, Type

import sqlalchemy
from sqlalchemy import cast, String, Integer, Boolean, DECIMAL, not_
from sqlalchemy.sql.operators import desc_op, asc_op
from marshmallow import Schema, fields as ma_fields

from flask_combo_jsonapi.schema import get_model_field
from flask_combo_jsonapi.utils import SPLIT_REL
from flask_combo_jsonapi.exceptions import InvalidFilters
from flask_combo_jsonapi.plugin import BasePlugin
from flask_combo_jsonapi.data_layers.shared import deserialize_field

from combojsonapi.utils import Relationship
from combojsonapi.postgresql_jsonb.schema import SchemaJSONB


TYPE_MARSHMALLOW_FIELDS = Type[Union[
    ma_fields.Email, ma_fields.Dict, ma_fields.List,
    ma_fields.Decimal, ma_fields.Url, ma_fields.DateTime, Any
]]
TYPE_PYTHON = Type[Union[int, bool, str, bytes, dict, list, Decimal, datetime.datetime]]


def is_seq_collection(obj):
    """
    является ли переданный объект set, list, tuple
    :param obj:
    :return bool:
    """
    return isinstance(obj, (list, set, tuple))


class PostgreSqlJSONB(BasePlugin):
    mapping_ma_field_to_type: Dict[TYPE_MARSHMALLOW_FIELDS, TYPE_PYTHON] = {
        ma_fields.Email: str,
        ma_fields.Dict: dict,
        ma_fields.List: list,
        ma_fields.Decimal: Decimal,
        ma_fields.Url: str,
        ma_fields.DateTime: datetime.datetime,
    }
    mapping_type_to_sql_type: Dict[TYPE_PYTHON, Any] = {
        str: String,
        bytes: String,
        Decimal: DECIMAL,
        int: Integer,
        bool: Boolean
    }

    def get_property_type(
            self, marshmallow_field: TYPE_MARSHMALLOW_FIELDS, schema: Optional[Schema] = None
    ) -> TYPE_PYTHON:
        if schema is not None:
            self.mapping_ma_field_to_type.update({
                v: k for k, v in schema.TYPE_MAPPING.items()
            })
        return self.mapping_ma_field_to_type[type(marshmallow_field)]

    def add_mapping_field_to_python_type(self, marshmallow_field: Any, type_python: TYPE_PYTHON) -> None:
        self.mapping_ma_field_to_type[marshmallow_field] = type_python

    def before_data_layers_sorting_alchemy_nested_resolve(self, self_nested: Any) -> Any:
        """
        Вызывается до создания сортировки в функции Nested.resolve, если после выполнения вернёт None, то
        дальше продолжиться работа функции resolve, если вернёт какое либо значения отличное от None, То
        функция resolve завершается, а результат hook функции передаётся дальше в стеке вызова
        :param Nested self_nested: instance Nested
        :return:
        """
        if SPLIT_REL in self_nested.sort_.get("field", ""):
            if self._isinstance_jsonb(self_nested.schema, self_nested.sort_["field"]):
                sort = self._create_sort(
                    self_nested,
                    marshmallow_field=self_nested.schema._declared_fields[self_nested.name],
                    model_column=self_nested.column,
                    order=self_nested.sort_["order"],
                )
                return sort, []

    def before_data_layers_filtering_alchemy_nested_resolve(self, self_nested: Any) -> Any:
        """
        Проверяем, если фильтр по jsonb полю, то создаём фильтр и возвращаем результат,
        если фильтр по другому полю, то возвращаем None
        :param self_nested:
        :return:
        """
        if not ({"or", "and", "not"} & set(self_nested.filter_)):

            if SPLIT_REL in self_nested.filter_.get("name", ""):
                if self._isinstance_jsonb(self_nested.schema, self_nested.filter_["name"]):
                    filter, joins = self._create_filter(
                        self_nested,
                        marshmallow_field=self_nested.schema._declared_fields[self_nested.name],
                        model_column=self_nested.column,
                        operator=self_nested.filter_["op"],
                        value=self_nested.value,
                    )
                    return filter, joins

    @classmethod
    def _isinstance_jsonb(cls, schema: Schema, filter_name: str) -> bool:
        """
        Определяем относится ли фильтр к relationship или к полю JSONB
        :param schema:
        :param filter_name:
        :return:
        """
        fields = filter_name.split(SPLIT_REL)
        for i, i_field in enumerate(fields):
            if isinstance(getattr(schema._declared_fields[i_field], "schema", None), SchemaJSONB):
                if i == (len(fields) - 1):
                    raise InvalidFilters(f"Invalid JSONB filter: {filter_name}")
                return True
            elif isinstance(schema._declared_fields[i_field], Relationship):
                schema = schema._declared_fields[i_field].schema
            else:
                return False

    def _create_sort(self, self_nested: Any, marshmallow_field, model_column, order):
        """
        Create sqlalchemy sort
        :param Nested self_nested:
        :param marshmallow_field:
        :param model_column: column sqlalchemy
        :param str order: asc | desc
        :return:
        """
        fields = self_nested.sort_["field"].split(SPLIT_REL)
        schema = getattr(marshmallow_field, "schema", None)
        if isinstance(marshmallow_field, Relationship):
            # If sorting by JSONB field of another model is in progress
            mapper = model_column.mapper.class_
            sqlalchemy_relationship_name = get_model_field(schema, fields[1])
            self_nested.sort_["field"] = SPLIT_REL.join(fields[1:])
            marshmallow_field = marshmallow_field.schema._declared_fields[fields[1]]
            model_column = getattr(mapper, sqlalchemy_relationship_name)
            return self._create_sort(self_nested, marshmallow_field, model_column, order)
        elif not isinstance(schema, SchemaJSONB):
            raise InvalidFilters(f"Invalid JSONB sort: {SPLIT_REL.join(self_nested.fields)}")
        self_nested.sort_["field"] = SPLIT_REL.join(fields[:-1])
        field_in_jsonb = fields[-1]

        try:
            for field in fields[1:]:
                marshmallow_field = marshmallow_field.schema._declared_fields[field]
        except KeyError as e:
            raise InvalidFilters(f'There is no "{e}" attribute in the "{fields[0]}" field.')

        if hasattr(marshmallow_field, f"_{order}_sql_sort_"):
            """
            У marshmallow field может быть реализована своя логика создания сортировки для sqlalchemy
            для определённого типа ('asc', 'desc'). Чтобы реализовать свою логику создания сортировка для
            определённого оператора необходимо реализовать в классе поля методы (название метода строится по
            следующему принципу `_<тип сортировки>_sql_filter_`). Также такой метод должен принимать ряд параметров
            * marshmallow_field - объект класса поля marshmallow
            * model_column - объект класса поля sqlalchemy
            """
            # All values between the first and last field will be the path to the desired value by which to sort,
            # so we write the path through "->"
            for field in fields[1:-1]:
                model_column = model_column.op("->")(field)
            model_column = model_column.op("->>")(field_in_jsonb)
            return getattr(marshmallow_field, f"_{order}_sql_sort_")(
                marshmallow_field=marshmallow_field, model_column=model_column
            )

        property_type = self.get_property_type(marshmallow_field=marshmallow_field, schema=self_nested.schema)

        for field in fields[1:-1]:
            model_column = model_column.op("->")(field)
        extra_field = model_column.op("->>")(field_in_jsonb)
        sort = ""
        order_op = desc_op if order == "desc" else asc_op
        if property_type in self.mapping_type_to_sql_type:
            if sqlalchemy.__version__ >= "1.1":
                sort = order_op(extra_field.astext.cast(self.mapping_type_to_sql_type[property_type]))
            else:
                sort = order_op(extra_field.cast(self.mapping_type_to_sql_type[property_type]))
        return sort

    def _create_filter(self, self_nested: Any, marshmallow_field, model_column, operator, value):
        """
        Create sqlalchemy filter
        :param Nested self_nested:
        :param marshmallow_field:
        :param model_column: column sqlalchemy
        :param operator:
        :param value:
        :return:
        """
        fields = self_nested.filter_["name"].split(SPLIT_REL)
        field_in_jsonb = fields[-1]
        schema = getattr(marshmallow_field, "schema", None)
        if isinstance(marshmallow_field, Relationship):
            # If filtering by JSONB field of another model is in progress
            mapper = model_column.mapper.class_
            sqlalchemy_relationship_name = get_model_field(schema, fields[1])
            self_nested.filter_["name"] = SPLIT_REL.join(fields[1:])
            marshmallow_field = marshmallow_field.schema._declared_fields[fields[1]]
            join_list = [[model_column]]
            model_column = getattr(mapper, sqlalchemy_relationship_name)
            filter, joins = self._create_filter(self_nested, marshmallow_field, model_column, operator, value)
            join_list += joins
            return filter, join_list
        elif not isinstance(schema, SchemaJSONB):
            raise InvalidFilters(f"Invalid JSONB filter: {SPLIT_REL.join(field_in_jsonb)}")
        self_nested.filter_["name"] = SPLIT_REL.join(fields[:-1])
        try:
            for field in fields[1:]:
                marshmallow_field = marshmallow_field.schema._declared_fields[field]
        except KeyError as e:
            raise InvalidFilters(f'There is no "{e}" attribute in the "{fields[0]}" field.')
        if hasattr(marshmallow_field, f"_{operator}_sql_filter_"):
            """
            У marshmallow field может быть реализована своя логика создания фильтра для sqlalchemy
            для определённого оператора. Чтобы реализовать свою логику создания фильтра для определённого оператора
            необходимо реализовать в классе поля методы (название метода строится по следующему принципу
            `_<тип оператора>_sql_filter_`). Также такой метод должен принимать ряд параметров
            * marshmallow_field - объект класса поля marshmallow
            * model_column - объект класса поля sqlalchemy
            * value - значения для фильтра
            * operator - сам оператор, например: "eq", "in"...
            """
            for field in fields[1:-1]:
                model_column = model_column.op("->")(field)
            model_column = model_column.op("->>")(field_in_jsonb)
            return (
                getattr(marshmallow_field, f"_{operator}_sql_filter_")(
                    marshmallow_field=marshmallow_field,
                    model_column=model_column,
                    value=value,
                    operator=self_nested.operator,
                ),
                [],
            )

        # Нужно проводить валидацию и делать десериализацию значение указанных в фильтре, так как поля Enum
        # например выгружаются как 'name_value(str)', а в БД хранится как просто число
        value = deserialize_field(marshmallow_field, value)

        property_type = self.get_property_type(marshmallow_field=marshmallow_field, schema=self_nested.schema)
        for field in fields[1:-1]:
            model_column = model_column.op("->")(field)
        extra_field = model_column.op("->>")(field_in_jsonb)
        filter_ = ""

        if property_type in {bool, int, str, bytes, Decimal}:
            field = cast(extra_field, self.mapping_type_to_sql_type[property_type])
            if value is None:
                filter_ = field.is_(None)
            else:
                filter_ = getattr(field, self_nested.operator)(value)

        elif property_type == list:
            filter_ = model_column.op("->")(field_in_jsonb).op("?")(value[0] if is_seq_collection(value) else value)
            if operator in ["notin", "notin_"]:
                filter_ = not_(filter_)

        return filter_, []
