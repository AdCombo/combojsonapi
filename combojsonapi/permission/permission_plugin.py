from collections import OrderedDict
from functools import wraps
from typing import Union, Tuple, List, Dict, Optional, Set, Type

from flask_combo_jsonapi.data_layers.alchemy import SqlalchemyDataLayer
from werkzeug.datastructures import ImmutableMultiDict
from marshmallow import class_registry, fields, Schema
from marshmallow.base import SchemaABC
from sqlalchemy import Column
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm import load_only, joinedload, ColumnProperty, Query

from flask_combo_jsonapi.exceptions import InvalidInclude, BadRequest
from flask_combo_jsonapi.querystring import QueryStringManager
from flask_combo_jsonapi.schema import get_model_field, get_related_schema
from flask_combo_jsonapi import Api
from flask_combo_jsonapi.utils import SPLIT_REL
from flask_combo_jsonapi.resource import ResourceList, ResourceDetail
from flask_combo_jsonapi.plugin import BasePlugin

from combojsonapi.permission.exceptions import PermissionException
from combojsonapi.utils import Relationship, get_decorators_for_resource
from combojsonapi.permission.permission_system import PermissionUser, PermissionToMapper, PermissionForGet


def get_columns_for_query(model) -> List[str]:
    """
    Получаем список название атрибутов в моделе, именно как они названы в моделе, т.е., если у нас вот так описано поле
    _permissions = Column('permissions', JSONB, nullable=False), то в columns будет _permissions.
    :param model: модель sqlalchemy
    :return:
    """
    columns = []
    for key, value in model.__dict__.items():
        # Оставляем только атрибуты Column
        if (isinstance(value, InstrumentedAttribute) or isinstance(value, Column)) and (
            hasattr(value, "prop") and isinstance(value.prop, ColumnProperty)
        ):
            columns.append(key)
    return columns


def get_required_fields(field_name: str, model) -> List[str]:
    """
    Вытаскиваем обязательные поля для загрузки из БД (нужно, например, когда в каком-либо проперти
    идет неявное обращение к другому отрибуту модели, который не был указан в запросе)
    :param field_name:
    :param model:
    :return:
    """
    required_fields = getattr(getattr(model, "Meta", {}), "required_fields", {})
    found_fields = []
    if field_name in required_fields:
        found_fields.extend(required_fields[field_name])
        for i_field in required_fields[field_name]:
            found_fields.extend(get_required_fields(i_field, model))
    return found_fields


def permission(method, request_type: str, many=False, decorators=None):
    @wraps(method)
    def wrapper(*args, **kwargs):
        permission_user = PermissionUser(request_type=request_type, many=many)
        return method(*args, **kwargs, _permission_user=permission_user)

    for i_decorator in decorators or []:
        wrapper = i_decorator(wrapper)
    return wrapper


class PermissionPlugin(BasePlugin):
    def __init__(self, strict: bool = False):
        """

        :param strict: отключать HTTP методы, если не указан ни один пермишен кейс (класс) для них.
                       Событийное API это не касается
        """
        self.strict = strict

    def after_route(
        self,
        resource: Type[Union[ResourceList, ResourceDetail]] = None,
        view=None,
        urls: Tuple[str] = None,
        self_json_api: Api = None,
        **kwargs,
    ) -> None:
        """
        Навешиваем декараторы (с инициализацией пермишенов) на роутеры
        :param resource:
        :param view:
        :param urls:
        :param self_json_api:
        :param kwargs:
        :return:
        """
        if getattr(resource, "_permission_plugin_inited", False):
            return

        if issubclass(resource, ResourceList):
            methods = ("get", "post")
        elif issubclass(resource, ResourceDetail):
            methods = ("get", "patch", "delete", "post")
        else:
            return

        for method in methods:
            self._permission_method(resource, method, self_json_api)
            # Для Post запроса в ResourceDetail не нужны пермишены, они берутся из ResourceList,
            # так как новый элемнт создаётся через ResourceList, а POST запросы в ResourceDetail
            # могут быть связанны с собыйтиным api EventsResource. В собыйтином api безопасность ложится
            # полностью на того кто разрабатывает его, также в любой момент можно обратиться к любому пермишену
            # из любого собыйтиного api, так как ссылка на истанц PermissionUser (активный в контектсе данного
            # api передаётся в kwargs['_permission_user']

        # Для избежание повторной инициализации плагина и навешивание декораторов с пермишеннами на API
        resource._permission_plugin_inited = True

    def _permission_method(
        self, resource: Type[Union[ResourceList, ResourceDetail]], type_method: str, self_json_api: Api
    ) -> None:
        """
        Обвешиваем ресурс декораторами с пермишенами, либо запрещаем першишен если он явно отключён
        :param Union[ResourceList, ResourceDetail] resource:
        :param str type_method:
        :param Api self_json_api:
        :return:
        """
        l_type = type_method.lower()
        u_type = type_method.upper()
        if issubclass(resource, ResourceList):
            methods = getattr(resource, "methods", ("GET", "POST"))
            type_ = "get_list" if l_type == "get" else l_type
            many = True
        elif issubclass(resource, ResourceDetail):
            methods = getattr(resource, "methods", ("GET", "PATCH", "DELETE"))
            type_ = l_type
            many = False
        else:
            return
        model = resource.data_layer["model"]
        if not hasattr(resource, l_type):
            return

        permissions = resource.data_layer.get(f"permission_{l_type}", [])
        PermissionToMapper.add_permission(type_=type_, model=model, permission_class=permissions)

        if self.strict and getattr(resource, "event", False) is False and u_type in methods:
            if not permissions:
                raise PermissionException(f"No permission case for {model.__name__} {type_}")

        if u_type in methods:
            old_method = getattr(resource, l_type)
            decorators = get_decorators_for_resource(resource, self_json_api)
            new_method = permission(old_method, request_type=l_type, many=many, decorators=decorators)
            setattr(resource, l_type, new_method)
        else:
            setattr(resource, l_type, self._resource_method_bad_request)

    @classmethod
    def _resource_method_bad_request(cls, *args, **kwargs):
        raise BadRequest("No method")

    @classmethod
    def _permission_for_link_schema(
        cls,
        *args,
        schema=None,
        prefix_name_column: str = "",
        columns: Optional[Union[List[str], Set[str]]] = None,
        is_nested: bool = False,
        **kwargs,
    ):
        """
        Навешиваем ограничения на схему, на которую ссылается поле
        :param args:
        :param schema:
        :param prefix_name_column: обрабатывать колонки, с которыми можно работать
        :param columns:
        :param is_nested: тип связи nested или relationship?
        :param kwargs:
        :return:
        """
        if not columns:
            return
        # уровень вложенности
        nesting_size_prefix_column: int = len(prefix_name_column.split(".")) if prefix_name_column else 0

        permission_column: List[str] = []
        _prefix = f"{prefix_name_column}." if prefix_name_column else ""
        for i_column in columns:
            if i_column.startswith(_prefix) and i_column != prefix_name_column:
                i_name = i_column.split(".")[nesting_size_prefix_column:]
                permission_column.append(i_name[0])
        permission_column = list(set(permission_column))

        # если не нашли ни одного разрешённого атрибута, значит все атрибуты доступны (иначе не нужно разрешать
        # выгружать в принципе схему)
        if not permission_column:
            return

        name_fields = []
        for i_name_field, i_field in schema.declared_fields.items():
            if i_name_field in permission_column:
                name_fields.append(i_name_field)

        only = getattr(schema, "only")
        only = set(only) if only else set(name_fields)
        # Оставляем поля только те, которые пользователь запросил через параметр fields[...]
        only &= set(name_fields)
        only = tuple(only)
        schema.fields = OrderedDict(**{name: val for name, val in schema.fields.items() if name in only})
        schema.dump_fields = OrderedDict(**{name: val for name, val in schema.fields.items() if name in only})

        schema.only = only

        include_data = tuple(i_include for i_include in getattr(schema, "include_data", []) if i_include in name_fields)
        setattr(schema, "include_data", include_data)

        # навешиваем ограничения на поля схемы, на которую указывает поле JSONB. Если
        # ограничений нет, то выгружаем все поля
        for i_field_name, i_field in schema.fields.items():
            if (
                i_field_name in permission_column
                and isinstance(i_field, fields.Nested)
                and not isinstance(i_field, Relationship)
            ):
                i_schema = i_field.schema
                if isinstance(i_schema, SchemaABC):
                    cls_schema = type(i_schema)
                else:
                    cls_schema = i_schema
                context = getattr(i_field.parent, "context", {})
                i_schema = cls_schema(
                    many=i_field.many,
                    only=i_field.only,
                    exclude=i_field.exclude,
                    context=context,
                    load_only=i_field._nested_normalized_option("load_only"),
                    dump_only=i_field._nested_normalized_option("dump_only"),
                )
                i_field._schema = i_schema
                cls._permission_for_link_schema(
                    schema=i_schema,
                    prefix_name_column=f"{prefix_name_column}.{i_field_name}" if prefix_name_column else i_field_name,
                    columns=columns,
                    is_nested=True,
                    **kwargs,
                )
        if not is_nested:
            # Выдераем из схем поля, которые пользователь не должен увидеть
            for i_include in getattr(schema, "include_data", []):
                if i_include in schema.fields:
                    cls._permission_for_link_schema(
                        schema=schema.declared_fields[i_include].__dict__["_Relationship__schema"],
                        prefix_name_column=f"{prefix_name_column}.{i_include}" if prefix_name_column else i_include,
                        columns=columns,
                        **kwargs,
                    )

    @classmethod
    def _permission_for_schema(cls, *args, schema=None, model=None, **kwargs):
        """
        Навешиваем ограничения на схему
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        permission_user: PermissionUser = kwargs.get("_permission_user")
        if permission_user is None:
            raise Exception("No permission for user")

        permission_column: Set[str] = permission_user.permission_for_get(model=model).columns_and_jsonb_columns
        cls._permission_for_link_schema(
            schema=schema, prefix_name_column="", columns=permission_column, **kwargs
        )

    def after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def data_layer_create_object_clean_data(
        self, *args, data: Dict = None, view_kwargs=None, join_fields: List[str] = None,
            self_json_api: SqlalchemyDataLayer = None, **kwargs
    ):
        """
        Обрабатывает данные, которые пойдут непосредственно на создание нового объекта
        :param args:
        :param Dict data: Данные, на основе которых будет создан новый объект
        :param view_kwargs:
        :param List[str] join_fields: список полей, которые являются ссылками на другие модели
        :param self_json_api:
        :param kwargs:
        :return:
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        return permission.permission_for_post_data(
            model=self_json_api.model, data=data, join_fields=join_fields, **view_kwargs
        )

    def data_layer_get_object_update_query(
        self, *args, query: Query = None, qs: QueryStringManager = None, view_kwargs=None, self_json_api=None, **kwargs
    ) -> Query:
        """
        Во время создания запроса к БД на выгрузку объекта. Тут можно пропатчить запрос к БД.
        Навешиваем ограничения на запрос, чтобы не тянулись поля из БД, которые данному
        пользователю не доступны. Также навешиваем фильтры, чтобы пользователь не смог увидеть
        записи, которые ему не доступны
        :param args:
        :param Query query: Сформированный запрос к БД
        :param QueryStringManager qs: список параметров для запроса
        :param view_kwargs: список фильтров для запроса
        :param self_json_api:
        :param kwargs:
        :return: возвращает пропатченный запрос к бд
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self_json_api.model)

        # Навешиваем фильтры (например пользователь не должен видеть некоторые поля)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        # Навешиваем ограничения по атрибутам (которые доступны & которые запросил пользователь)
        name_columns = permission_for_get.columns
        if qs:
            user_requested_columns = qs.fields.get(self_json_api.resource.schema.Meta.type_)
            if user_requested_columns:
                name_columns = list(set(name_columns) & set(user_requested_columns))
        # Убираем relationship поля
        name_columns = [i_name for i_name in name_columns if i_name in self_json_api.model.__table__.columns.keys()]
        required_columns_names = []
        for i_name in name_columns:
            required_columns_names.extend(get_required_fields(i_name, self_json_api.model))
        name_columns = list(set(name_columns) | set(required_columns_names))

        query = query.options(load_only(*name_columns))
        if qs:
            query = self._eagerload_includes(query, qs, permission, self_json_api=self_json_api)

        # Запретим использовать стандартную функцию eagerload_includes для присоединения сторонних молелей
        self_json_api.eagerload_includes = lambda x, y: x
        return query

    def data_layer_get_collection_update_query(
        self, *args, query: Query = None, qs: QueryStringManager = None, view_kwargs=None, self_json_api=None, **kwargs
    ) -> Query:
        """
        Во время создания запроса к БД на выгрузку объектов. Тут можно пропатчить запрос к БД
        :param args:
        :param Query query: Сформированный запрос к БД
        :param QueryStringManager qs: список параметров для запроса
        :param view_kwargs: список фильтров для запроса
        :param self_json_api:
        :param kwargs:
        :return: возвращает пропатченный запрос к бд
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self_json_api.model)

        # Навешиваем фильтры (например пользователь не должен видеть некоторые поля)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        # Навешиваем ограничения по атрибутам (которые доступны & которые запросил пользователь)
        name_columns = permission_for_get.columns
        user_requested_columns = qs.fields.get(self_json_api.resource.schema.Meta.type_)
        if user_requested_columns:
            name_columns = list(set(name_columns) & set(user_requested_columns))

        # required fields (from Meta.required_fields)
        required_columns_names = []
        for i_name in name_columns:
            required_columns_names.extend(get_required_fields(i_name, self_json_api.model))

        # remove relationship fields
        name_columns = list(set(name_columns) & set(get_columns_for_query(self_json_api.model)))
        name_columns = list(set(name_columns) | set(required_columns_names))

        query = query.options(load_only(*name_columns))

        # Запретим использовать стандартную функцию eagerload_includes для присоединения сторонних молелей
        setattr(self_json_api, "eagerload_includes", False)
        query = self._eagerload_includes(query, qs, permission, self_json_api=self_json_api)
        return query

    def data_layer_update_object_clean_data(
        self,
        *args,
        data: Dict = None,
        obj=None,
        view_kwargs=None,
        join_fields: List[str] = None,
        self_json_api=None,
        **kwargs,
    ) -> Dict:
        """
        Обрабатывает данные, которые пойдут непосредственно на обновления объекта
        :param args:
        :param Dict data: Данные, на основе которых будет создан новый объект
        :param obj: Объект, который будет обновлён
        :param view_kwargs:
        :param List[str] join_fields: список полей, которые являются ссылками на другие модели
        :param self_json_api:
        :param kwargs:
        :return: возвращает обновлённый набор данных для нового объекта
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        clean_data = permission.permission_for_patch_data(
            model=self_json_api.model, data=data, obj=obj, join_fields=join_fields, **view_kwargs
        )
        return clean_data

    def data_layer_delete_object_clean_data(
        self, *args, obj=None, view_kwargs=None, self_json_api=None, **kwargs
    ) -> None:
        """
        Выполняется до удаления объекта в БД
        :param args:
        :param obj: удаляемый объект
        :param view_kwargs:
        :param self_json_api:
        :param kwargs:
        :return:
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission.permission_for_delete(model=self_json_api.model, obj=obj, **view_kwargs)

    @classmethod
    def _get_permission_user(cls, view_kwargs) -> PermissionUser:
        permission_user = view_kwargs.get("_permission_user")
        if permission_user is not None:
            return permission_user
        raise Exception("No permission for user")

    @classmethod
    def _get_model(cls, model, name_foreign_key: str) -> str:
        """
        Возвращает модель, на которую указывает "внешний ключ"
        :param model: модель, из которой взят "внешний ключ" name_foreign_key
        :param str name_foreign_key: "внешний ключ", например "manager_id" или "manager_id.group_id"
        :return:
        """
        mapper = model
        for i_name_foreign_key in name_foreign_key.split(SPLIT_REL):
            mapper_old = mapper
            mapper = getattr(mapper_old, i_name_foreign_key, None)
            if mapper is None:
                # Внешний ключ должен присутствовать в маппере
                raise ValueError("No foreign key %s in mapper %s" % (i_name_foreign_key, mapper_old.__name__))
            mapper = mapper.mapper.class_
        return mapper

    @classmethod
    def _is_access_foreign_key(cls, name_foreign_key: str, model, permission: PermissionUser = None) -> bool:
        """
        Проверяет есть ли доступ к данному внешнему ключу
        :param name_foreign_key: название внешнего ключа, например "manager_id" или "manager_id.group_id"
        :param model: маппер, с которого начинается проверка внешнего ключа name_foreign_key
        :return:
        """
        permission_for_get: PermissionForGet = permission.permission_for_get(model)
        name_foreign_key = name_foreign_key.split(SPLIT_REL)[-1]
        if name_foreign_key not in permission_for_get.columns:
            return False
        return True

    @classmethod
    def _update_qs_fields(
        cls, type_schema: str, fields: List[str], qs: QueryStringManager = None, name_foreign_key: str = None
    ) -> None:
        """
        Обновляем fields в qs для работы схемы (чтобы она не обращалась к полям, которые не доступны пользователю)
        :param str type_schema: название типа схемы Meta.type_
        :param List[str] fields: список доступных полей
        :param QueryStringManager qs: параметры из get запроса
        :param str name_foreign_key: название поля в схеме, которое ссылается на схему type_schema
        :return:
        """
        old_fields = qs._get_key_values("fields")
        if type_schema in old_fields:
            new_fields = list(set(old_fields.get(type_schema, [])) & set(fields))
        else:
            new_fields = fields
        new_qs = {k: v for k, v in qs.qs.items() if v != ""}
        include = new_qs.get("include", "").split(",")
        if not new_fields and include and name_foreign_key in include:
            new_qs["include"] = ",".join([inc for inc in include if inc != name_foreign_key])
        else:
            new_qs[f"fields[{type_schema}]"] = ",".join(new_fields)
        qs.qs = ImmutableMultiDict(new_qs)

    @classmethod
    def _get_access_fields_in_schema(
        cls,
        name_foreign_key: str,
        cls_schema,
        permission_user: PermissionUser = None,
        model=None,
        qs: QueryStringManager = None,
    ) -> List[str]:
        """
        Получаем список названий полей, которые доступны пользователю и есть в схеме
        :param name_foreign_key: название "внешнего ключа"
        :param cls_schema: класс со схемой
        :param PermissionUser permission_user: пермишены для пользователя
        :param model:
        :return:
        """
        # Вытаскиваем модель на которую ссылается "внешний ключ", чтобы получить ограничения на неё
        # для данного пользователя
        field_foreign_key = get_model_field(cls_schema, name_foreign_key)
        mapper = cls._get_model(model, field_foreign_key)
        current_schema = cls._get_schema(cls_schema, name_foreign_key)
        permission_for_get: PermissionForGet = permission_user.permission_for_get(mapper)
        # ограничиваем выгрузку полей в соответствие с пермишенами
        name_columns = []
        if permission_for_get.columns is not None:
            name_columns = list(set(current_schema._declared_fields.keys()) & permission_for_get.columns)
        cls._update_qs_fields(current_schema.Meta.type_, name_columns, qs=qs, name_foreign_key=name_foreign_key)
        return name_columns

    @classmethod
    def _get_schema(cls, current_schema: SchemaABC, obj: str):
        """
        Получаем схему на которую ссылается Nested
        :param current_schema: схема изначальная
        :param obj: поле в current_schema
        :return:
        """
        related_schema_cls = get_related_schema(current_schema, obj)

        if isinstance(related_schema_cls, SchemaABC):
            related_schema_cls = related_schema_cls.__class__
        elif isinstance(related_schema_cls, str):
            related_schema_cls = class_registry.get_class(related_schema_cls)

        return related_schema_cls

    @classmethod
    def _get_or_update_joinedload_object(cls, joinedload_object, qs: QueryStringManager, permission_user: PermissionUser,
                                         model, current_schema: Schema, field: str, include: str, path_index: int):
        """
        Checks permissions and makes query joinedload option for accessed fields.
        :param joinedload_object: sqlalchemy joinedload or None
        :param qs:
        :param permission_user:
        :param model:
        :param current_schema:
        :param field: attribute of the schema field, pointing to a field from another model
        :param include: param or part of dot-splitted param from querystring "include"
        :param path_index:
        :return:
        """
        if joinedload_object is None:
            joinedload_object = joinedload(getattr(model, field))
        else:
            joinedload_object = joinedload_object.joinedload(getattr(model, field))

        # ограничиваем список полей (которые доступны & которые запросил пользователь)
        name_columns = cls._get_access_fields_in_schema(include, current_schema, permission_user, model=model, qs=qs)
        related_schema_cls = cls._get_schema(current_schema, include)
        user_requested_columns = qs.fields.get(related_schema_cls.Meta.type_)
        if user_requested_columns:
            name_columns = set(name_columns) & set(user_requested_columns)
        # Убираем relationship поля
        name_columns = set(name_columns) & set(
            get_columns_for_query(joinedload_object.path[path_index].property.mapper.class_)
        )
        required_columns_names = []
        for i_name in name_columns:
            required_columns_names.extend(
                get_required_fields(i_name, joinedload_object.path[path_index].property.mapper.class_)
            )
        name_columns = list(set(name_columns) | set(required_columns_names))

        joinedload_object.load_only(*list(name_columns))
        return joinedload_object, related_schema_cls

    @classmethod
    def _get_joinedload_object_for_splitted_include(cls, include: str, qs: QueryStringManager,
                                                    permission_user: PermissionUser, current_schema: Schema, model):
        """
        Processes dot-splitted params from "include" and makes joinedload option for query.
        """
        joinedload_object = None
        for i, obj in enumerate(include.split(SPLIT_REL)):
            try:
                field = get_model_field(current_schema, obj)
            except Exception as e:
                raise InvalidInclude(str(e))

            if cls._is_access_foreign_key(obj, model, permission_user) is False:
                continue

            joinedload_object, current_schema = cls._get_or_update_joinedload_object(
                joinedload_object=joinedload_object, qs=qs, permission_user=permission_user, model=model,
                current_schema=current_schema, field=field, include=obj, path_index=i
            )
            try:
                model = cls._get_model(model, field)
            except ValueError as e:
                raise InvalidInclude(str(e))

        return joinedload_object

    @classmethod
    def _get_joinedload_object_for_include(cls, include, qs, permission_user, current_schema, model):
        """
        Processes params from "include" and makes joinedload option for query
        """
        try:
            field = get_model_field(current_schema, include)
        except Exception as e:
            raise InvalidInclude(str(e))

        joinedload_object, _ = cls._get_or_update_joinedload_object(joinedload_object=None, model=model, path_index=0,
                                                                    permission_user=permission_user, qs=qs, field=field,
                                                                    current_schema=current_schema, include=include)
        return joinedload_object

    @classmethod
    def _eagerload_includes(cls, query: Query, qs: QueryStringManager, permission_user: PermissionUser = None,
                            self_json_api: SqlalchemyDataLayer = None):
        """
        Processes "include" param from querystring and applies permissions for included models.
        Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter

        :param Query query: sqlalchemy queryset
        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param PermissionUser permission_user: пермишены для пользователя
        :param self_json_api:
        :return Query: the query with includes eagerloaded
        """
        current_schema = self_json_api.resource.schema
        model = self_json_api.model
        for include in qs.include:
            if SPLIT_REL in include:
                joinedload_object = cls._get_joinedload_object_for_splitted_include(include, qs, permission_user,
                                                                                    current_schema, model)
            else:
                # Возможно пользовать неимеет доступа, к данному внешнему ключу
                if cls._is_access_foreign_key(include, model, permission_user) is False:
                    continue
                joinedload_object = cls._get_joinedload_object_for_include(include, qs, permission_user,
                                                                           current_schema, model)
            query = query.options(joinedload_object)

        return query
