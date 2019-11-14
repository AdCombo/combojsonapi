from collections import OrderedDict
from functools import wraps
from typing import Union, Tuple, List, Dict

from werkzeug.datastructures import ImmutableMultiDict
from marshmallow import class_registry, fields
from marshmallow.base import SchemaABC
from sqlalchemy import Column
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm import load_only, joinedload, ColumnProperty, Query

from flask_rest_jsonapi.exceptions import InvalidInclude, BadRequest
from flask_rest_jsonapi.querystring import QueryStringManager
from flask_rest_jsonapi.schema import get_model_field, get_related_schema
from flask_rest_jsonapi import Api
from flask_rest_jsonapi.utils import SPLIT_REL
from flask_rest_jsonapi.resource import ResourceList, ResourceDetail
from flask_rest_jsonapi.plugin import BasePlugin

from combojsonapi.utils import Relationship, get_decorators_for_resource
from combojsonapi.permission.permission_system import PermissionUser, PermissionToMapper, PermissionForGet


def get_columns_for_query(model) -> List[str]:
    """
    Getting list of attributes' names exactly like they're named in the model.
    E. g. field _permissions = Column('permissions', JSONB, nullable=False), will get to columns as _permissions.
    :param model: sqlalchemy model
    :return:
    """
    columns = []
    for key, value in model.__dict__.items():
        # Only Column attributes are retained
        if (isinstance(value, InstrumentedAttribute) or isinstance(value, Column)) \
                and isinstance(getattr(value, 'prop'), ColumnProperty):
            columns.append(key)
    return columns


def permission(method, request_type: str, many=False, decorators=None):

    @wraps(method)
    def wrapper(*args, **kwargs):
        permission_user = PermissionUser(request_type=request_type, many=many)
        return method(*args, **kwargs, _permission_user=permission_user)

    decorators = decorators if decorators else []
    for i_decorator in decorators:
        wrapper = i_decorator(wrapper)
    return wrapper


class PermissionPlugin(BasePlugin):

    def after_route(self,
                    resource: Union[ResourceList, ResourceDetail] = None,
                    view=None,
                    urls: Tuple[str] = None,
                    self_json_api: Api = None,
                    **kwargs) -> None:
        """
        Putting up decorators (which initialize permissions) on routers
        :param resource:
        :param view:
        :param urls:
        :param self_json_api:
        :param kwargs:
        :return:
        """
        if getattr(resource, '_permission_plugin_inited', False):
            return

        if issubclass(resource, ResourceList):
            methods = ('get', 'post')
        elif issubclass(resource, ResourceDetail):
            methods = ('get', 'patch', 'delete', 'post')
        else:
            return

        for method in methods:
            self._permission_method(resource, method, self_json_api)
            # ResourceDetail doesn't require permissions for POST request, since they're provided by ResourceList,
            # That's because new objects are created with ResourceList, and POST requests to to ResourceDetail
            # might be linked to event-based API EventsResource.
            #
            # In event-based API no security features are provided, and they must be implemented solely by its developer.
            # However, event-based API has access to any permission, since it a link to PermissionUser object (active, 
            # in API context) is passed in kwargs['_permission_user']

        resource._permission_plugin_inited = True

    @classmethod
    def _permission_method(cls, resource: Union[ResourceList, ResourceDetail],
                           type_method: str, self_json_api: Api) -> None:
        """
        Decorating the resource with permissions methods, or forbidding access to a method if it's disabled
        :param Union[ResourceList, ResourceDetail] resource:
        :param str type_method:
        :param Api self_json_api:
        :return:
        """
        l_type = type_method.lower()
        u_type = type_method.upper()
        if issubclass(resource, ResourceList):
            methods = getattr(resource, 'methods', ('GET', 'POST'))
            type_ = 'get_list' if l_type == 'get' else l_type
        elif issubclass(resource, ResourceDetail):
            methods = getattr(resource, 'methods', ('GET', 'PATCH', 'DELETE'))
            type_ = l_type
        else:
            return
        model = resource.data_layer['model']
        if not hasattr(resource, l_type):
            return

        old_method = getattr(resource, l_type)

        decorators = get_decorators_for_resource(resource, self_json_api)
        new_method = permission(old_method, request_type=l_type, many=True, decorators=decorators)
        if u_type in methods:
            setattr(resource, l_type, new_method)
        else:
            setattr(resource, l_type, cls._resource_method_bad_request)

        permissions = resource.data_layer.get(f'permission_{l_type}', [])
        PermissionToMapper.add_permission(type_=type_, model=model, permission_class=permissions)

    @classmethod
    def _resource_method_bad_request(cls, *args, **kwargs):
        raise BadRequest('No method')

    @classmethod
    def _permission_for_schema(cls, *args, schema=None, model=None, **kwargs):
        """
        Adding permissions to a schema
        :param args:
        :param schema:
        :param model:
        :param kwargs:
        :return:
        """
        pass
        permission_user: PermissionUser = kwargs.get('_permission_user')
        if permission_user is None:
            raise Exception("No permission for user")
        name_fields = []
        for i_name_field, i_field in schema.declared_fields.items():
            if isinstance(i_field, Relationship) \
                    or i_name_field in permission_user.permission_for_get(model=model).columns:
                name_fields.append(i_name_field)
        only = getattr(schema, 'only')
        only = set(only) if only else set(name_fields)
        # Leaving only fields requested by user in fields[...] parameter
        only &= set(name_fields)
        only = tuple(only)
        schema.fields = OrderedDict(**{name: val for name, val in schema.fields.items() if name in only})
        schema.fields = OrderedDict(**{name: val for name, val in schema.fields.items() if name in only})
        schema.dump_fields = OrderedDict(**{name: val for name, val in schema.fields.items() if name in only})

        schema.only = only

        # Adding restrictions to fields of a schema, to which JSONB field points. If there's
        # no restrictions, will return all fields
        for i_field_name, i_field in schema.fields.items():
            jsonb_only = permission_user.permission_for_get(model=model).columns_for_jsonb(i_field_name)
            if isinstance(i_field, fields.Nested) and \
                    getattr(getattr(i_field.schema, 'Meta', object), 'filtering', False) and \
                    jsonb_only is not None:
                i_field.schema.only = tuple(jsonb_only)
                i_field.schema.fields = OrderedDict(**{name: val for name, val in i_field.schema.fields.items() if name in jsonb_only})

        include_data = tuple(i_include for i_include in getattr(schema, 'include_data', []) if i_include in name_fields)
        setattr(schema, 'include_data', include_data)
        # Removing fields user shouldn't access
        for i_include in getattr(schema, 'include_data', []):
            if i_include in schema.fields:
                field = get_model_field(schema, i_include)
                i_model = cls._get_model(model, field)
                cls._permission_for_schema(schema=schema.declared_fields[i_include].__dict__['_Relationship__schema'],
                                           model=i_model, **kwargs)

    def after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs):
        self._permission_for_schema(self, *args, schema=schema, model=model, **kwargs)

    def data_layer_create_object_clean_data(self, *args, data: Dict = None, view_kwargs=None,
                                            join_fields: List[str] = None, self_json_api=None, **kwargs):
        """
        Parses input data and returns parsed data set, from which a new object will be created.
        :param args:
        :param Dict data: deserialized input data set
        :param view_kwargs:
        :param List[str] join_fields: fields which are linked to other models
        :param self_json_api:
        :param kwargs:
        :return:
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        return permission.permission_for_post_data(model=self_json_api.model, data=data, join_fields=join_fields, **view_kwargs)

    def data_layer_get_object_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                           view_kwargs=None, self_json_api=None, **kwargs) -> Query:
        """
        Called during database query creation for updating a single object. Query can be patched here, if needed.
        Setting up restrictions so user won't access attributes and rows he is forbidden to view.
        :param args:
        :param Query query: generated database query
        :param QueryStringManager qs: query parameters list
        :param view_kwargs: filters list for the query
        :param self_json_api:
        :param kwargs:
        :return: patched DB query
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self_json_api.model)

        # Setting up filters (e. g. user is restricted to view some rows)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        # Setting up restrictions for attributes: accessible & requested by user)
        name_columns = permission_for_get.columns
        user_requested_columns = qs.fields.get(self_json_api.resource.schema.Meta.type_)
        if user_requested_columns:
            name_columns = list(set(name_columns) & set(user_requested_columns))
        # Removing relationship fields
        name_columns = [i_name for i_name in name_columns if i_name in self_json_api.model.__table__.columns.keys()]

        query = query.options(load_only(*name_columns))
        query = self._eagerload_includes(query, qs, permission, self_json_api=self_json_api)

        # Disable default eagerload_includes method for attaching additional models
        self_json_api.eagerload_includes = lambda x, y: x
        return query

    def data_layer_get_collection_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                               view_kwargs=None, self_json_api=None, **kwargs) -> Query:
        """
        Called during database query creation for updating multiple objects. Query can be patched here, if needed.
        :param args:
        :param Query query: database query
        :param QueryStringManager qs: query parameters list
        :param view_kwargs: filters list for the query
        :param self_json_api:
        :param kwargs:
        :return: patched DB query
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission_for_get: PermissionForGet = permission.permission_for_get(self_json_api.model)

        # Setting up filters (e. g. user is restricted to view some rows)
        for i_join in permission_for_get.joins:
            query = query.join(*i_join)
        query = query.filter(*permission_for_get.filters)

        # Setting up restrictions for attributes: accessible & requested by user)
        name_columns = permission_for_get.columns
        user_requested_columns = qs.fields.get(self_json_api.resource.schema.Meta.type_)
        if user_requested_columns:
            name_columns = list(set(name_columns) & set(user_requested_columns))
        # Removing relationship fields
        name_columns = list(set(name_columns) & set(get_columns_for_query(self_json_api.model)))

        query = query.options(load_only(*name_columns))

        # Disable default eagerload_includes method for attaching additional models
        setattr(self_json_api, 'eagerload_includes', False)
        query = self._eagerload_includes(query, qs, permission, self_json_api=self_json_api)
        return query

    def data_layer_update_object_clean_data(self, *args, data: Dict = None, obj=None, view_kwargs=None,
                                            join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict:
        """
        Parses data for the object to be updated.
        :param args:
        :param Dict data: generated database query;
        :param obj: query parameters list;
        :param view_kwargs:
        :param List[str] join_fields: link to Api instance.
        :param self_json_api:
        :param kwargs:
        :return: parsed data set
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        clean_data = permission.permission_for_patch_data(model=self_json_api.model, data=data, obj=obj,
                                                          join_fields=join_fields, **view_kwargs)
        return clean_data

    def data_layer_delete_object_clean_data(self, *args, obj=None, view_kwargs=None, self_json_api=None, **kwargs) -> None:
        """
        Called before deleting object from the database.
        :param args:
        :param obj: object to delete;
        :param view_kwargs:
        :param self_json_api: link to Api instance.
        :param kwargs:
        :return:
        """
        permission: PermissionUser = self._get_permission_user(view_kwargs)
        permission.permission_for_delete(model=self_json_api.model, obj=obj, **view_kwargs)

    @classmethod
    def _get_permission_user(cls, view_kwargs) -> PermissionUser:
        permission_user = view_kwargs.get('_permission_user')
        if permission_user is not None:
            return permission_user
        raise Exception("No permission for user")

    @classmethod
    def _get_model(cls, model, name_foreign_key: str) -> str:
        """
        Returns a model to which "foreign key" point
        :param model: model, from which "foreign key" name_foreign_key is taken
        :param str name_foreign_key: "foreign key" itself, e. g. "manager_id" or "manager_id.group_id"
        :return:
        """
        mapper = model
        for i_name_foreign_key in name_foreign_key.split(SPLIT_REL):
            mapper_old = mapper
            mapper = getattr(mapper_old, i_name_foreign_key, None)
            if mapper is None:
                # Foreign key must be in the mapper
                raise ValueError('Not foreign key %s in mapper %s' % (i_name_foreign_key, mapper_old.__name__))
            mapper = mapper.mapper.class_
        return mapper

    @classmethod
    def _is_access_foreign_key(cls, name_foreign_key: str, model, permission: PermissionUser = None) -> bool:
        """
        Checks if foreign key is accessible
        :param name_foreign_key: foreign key name, e. g. "manager_id" or "manager_id.group_id"
        :param model: model from which name_foreign_key check begins
        :return:
        """
        permission_for_get: PermissionForGet = permission.permission_for_get(model)
        name_foreign_key = name_foreign_key.split(SPLIT_REL)[-1]
        if name_foreign_key not in permission_for_get.columns:
            return False
        return True

    @classmethod
    def _update_qs_fields(cls, type_schema: str, fields: List[str], qs: QueryStringManager = None,
                          name_foreign_key: str = None) -> None:
        """
        Updates qs fields for the schema to work, so it doesn't access restricted fields
        :param str type_schema: Schema type Meta.type_ name
        :param List[str] fields: allowed fields list
        :param QueryStringManager qs: GET request params
        :param str name_foreign_key: schema field name linking to schema type_schema
        :return:
        """
        old_fields = qs._get_key_values('fields')
        if type_schema in old_fields:
            new_fields = list(set(old_fields.get(type_schema, [])) & set(fields))
        else:
            new_fields = fields
        new_qs = {k: v for k, v in qs.qs.items() if v != ''}
        include = new_qs.get('include', '').split(',')
        if not new_fields and include and name_foreign_key in include:
            new_qs['include'] = ','.join([inc for inc in include if inc != name_foreign_key])
        else:
            new_qs[f'fields[{type_schema}]'] = ','.join(new_fields)
        qs.qs = ImmutableMultiDict(new_qs)

    @classmethod
    def _get_access_fields_in_schema(cls, name_foreign_key: str, cls_schema, permission: PermissionUser = None,
                                     model=None, qs: QueryStringManager = None) -> List[str]:
        """
        Get list of schema field names accessible to the user
        :param name_foreign_key: "foreign key" name
        :param cls_schema: schema class
        :param PermissionUser permission: user permissions
        :param model:
        :return:
        """
        # Exctracting model to which "foreign key" links, to get restrictions for the current user
        field_foreign_key = get_model_field(cls_schema, name_foreign_key)
        mapper = cls._get_model(model, field_foreign_key)
        current_schema = cls._get_schema(cls_schema, name_foreign_key)
        permission_for_get: PermissionForGet = permission.permission_for_get(mapper)
        # Restricting fields according to permissions
        name_columns = []
        if permission_for_get.columns is not None:
            name_columns = list(set(current_schema._declared_fields.keys()) & permission_for_get.columns)
        cls._update_qs_fields(current_schema.Meta.type_, name_columns, qs=qs, name_foreign_key=name_foreign_key)
        return name_columns

    @classmethod
    def _get_schema(cls, current_schema: SchemaABC, obj: str):
        """
        Get the schema Nested links to
        :param current_schema: initial schema
        :param obj: field in the current_schema
        :return:
        """
        related_schema_cls = get_related_schema(current_schema, obj)

        if isinstance(related_schema_cls, SchemaABC):
            related_schema_cls = related_schema_cls.__class__
        else:
            related_schema_cls = class_registry.get_class(related_schema_cls)

        return related_schema_cls

    @classmethod
    def _eagerload_includes(cls, query, qs, permission: PermissionUser = None, self_json_api=None):
        """Redefined and improved eagerload_includes method of SqlalchemyDataLayer class, so it restricts (per passed permission)
        which fields of a model, to which foreign key links, are returned from database
        Use eagerload feature of sqlalchemy to optimize data retrieval for include querystring parameter

        :param Query query: sqlalchemy queryset
        :param QueryStringManager qs: a querystring manager to retrieve information from url
        :param PermissionUser permission: user permissions
        :param self_json_api:
        :return Query: the query with includes eagerloaded
        """
        for include in qs.include:
            joinload_object = None

            if SPLIT_REL in include:
                current_schema = self_json_api.resource.schema
                model = self_json_api.model
                for i, obj in enumerate(include.split(SPLIT_REL)):
                    try:
                        field = get_model_field(current_schema, obj)
                    except Exception as e:
                        raise InvalidInclude(str(e))

                    # User might not have access to this external key
                    if cls._is_access_foreign_key(obj, model, permission) is False:
                        continue

                    if joinload_object is None:
                        joinload_object = joinedload(getattr(model, field))
                    else:
                        joinload_object = joinload_object.joinedload(getattr(model, field))

                    # Restricting fields liks (accessible to & requested by a user)
                    name_columns = cls._get_access_fields_in_schema(obj, current_schema, permission, model=model, qs=qs)
                    current_schema = cls._get_schema(current_schema, obj)
                    user_requested_columns = qs.fields.get(current_schema.Meta.type_)
                    if user_requested_columns:
                        name_columns = set(name_columns) & set(user_requested_columns)
                    # Removing relationship fields
                    name_columns = (
                        set(name_columns) & set(get_columns_for_query(joinload_object.path[i].property.mapper.class_))
                    )

                    joinload_object.load_only(*list(name_columns))

                    try:
                        # Requested external key might not exist
                        model = cls._get_model(model, field)
                    except ValueError as e:
                        raise InvalidInclude(str(e))

            else:
                try:
                    field = get_model_field(self_json_api.resource.schema, include)
                except Exception as e:
                    raise InvalidInclude(str(e))

                # User might not have access to this external key
                if cls._is_access_foreign_key(include, self_json_api.model, permission) is False:
                    continue

                joinload_object = joinedload(getattr(self_json_api.model, field))

                # Restricting fields liks (accessible to & requested by a user)
                name_columns = cls._get_access_fields_in_schema(include, self_json_api.resource.schema, permission,
                                                                model=self_json_api.model, qs=qs)
                related_schema_cls = get_related_schema(self_json_api.resource.schema, include)
                user_requested_columns = qs.fields.get(related_schema_cls.Meta.type_)
                if user_requested_columns:
                    name_columns = set(name_columns) & set(user_requested_columns)
                # Removing relationship fields
                name_columns = (
                    set(name_columns) & set(get_columns_for_query(joinload_object.path[0].property.mapper.class_))
                )

                joinload_object.load_only(*list(name_columns))

            query = query.options(joinload_object)

        return query
