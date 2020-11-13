from functools import wraps
from unittest import mock

import pytest
from flask_combo_jsonapi import ResourceList, ResourceDetail, Api, JsonApiException
from flask_combo_jsonapi.data_layers.alchemy import SqlalchemyDataLayer
from flask_combo_jsonapi.exceptions import BadRequest, InvalidInclude
from flask_combo_jsonapi.querystring import QueryStringManager
from marshmallow import fields, Schema
from marshmallow_jsonapi import Schema as JsonApiSchema
from marshmallow_jsonapi.fields import Relationship
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker

from combojsonapi.permission import PermissionPlugin, PermissionMixin, PermissionToMapper, PermissionUser, \
    PermissionForGet
from combojsonapi.permission.exceptions import PermissionException
from combojsonapi.permission.permission_plugin import get_columns_for_query, get_required_fields, permission
from tests.test_permission import Base


JsonApi = Api()


class MyModel(Base):
    __tablename__ = "model"
    # we need a PK
    id = Column(Integer, primary_key=True)
    # creating a column
    model_type = Column(Integer)
    # for no reason creating a column
    # which takes the same name
    model_entity = Column("model_type", Integer)


class ModelWithMeta(Base):
    __tablename__ = 'model_with_meta'

    class Meta:
        required_fields = {
            'description': ['name', 'type'],
            'name': ['flags'],
        }

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(Integer)
    flags = Column(Integer)
    description = Column(String)
    settings = Column(String)
    related_model_id = Column(Integer)


class RelatedModel(Base):
    __tablename__ = 'related_model'

    id = Column(Integer, primary_key=True)
    other_field = Column(String)


mock_mapper = mock.Mock()
mock_mapper.class_ = RelatedModel
ModelWithMeta.related_model_id.mapper = mock_mapper


class RelatedModelSchema(JsonApiSchema):
    class Meta:
        model = RelatedModel
        type_ = 'related_model'
    id = fields.Integer()
    other_field = fields.String()


class SettingsSchema(Schema):
    first_attr = fields.Integer()
    second_attr = fields.String()


class ModelWithMetaSchema(JsonApiSchema):
    class Meta:
        model = ModelWithMeta
        type_ = 'model_with_meta'

    id = fields.Integer()
    name = fields.String()
    type = fields.Integer()
    flags = fields.Integer()
    description = fields.Integer()
    settings = fields.Nested(SettingsSchema)
    related_model_id = Relationship(nested=RelatedModelSchema, schema='RelatedModelSchema', type_='related_model')


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:")
    ModelWithMeta.metadata.create_all(engine)
    RelatedModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def session(engine):
    session = sessionmaker(bind=engine)
    return session()


class SomePermission(PermissionMixin):
    def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
        self.permission_for_get.allow_columns = [
            'name', 'type', 'description', 'settings.first_attr'
        ], 1
        return self.permission_for_get

    def patch_data(self, *args, data=None, obj=None, user_permission: PermissionUser = None, **kwargs) -> dict:
        data['patched_by_some_permission'] = True
        return data

    def delete(self, *args, obj=None, user_permission: PermissionUser = None, **kwargs) -> bool:
        return obj.deletable


class PermissionWithJoinsAndFilters(PermissionMixin):
    def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
        self.permission_for_get.allow_columns = [
            'name', 'type', 'description', 'settings.first_attr'
        ], 1
        self.permission_for_get.filters = [ModelWithMeta.type != 3]
        self.permission_for_get.joins = [(RelatedModel, RelatedModel.id == ModelWithMeta.related_model_id)]
        return self.permission_for_get


def test_get_columns_for_query():
    """
    Test if the model with some names
    overlapping is processed without errors
    :return:
    """

    res = get_columns_for_query(MyModel)
    # expecting columns names
    assert res == ["id", "model_entity"]


@pytest.mark.parametrize('field_name, result_fields', (
        pytest.param('flags', [], id='no required fields'),
        pytest.param('name', ['flags'], id='own required fields'),
        pytest.param('description', ['name', 'type', 'flags'], id='own required fields and their required fields')

))
def test_get_required_fields(field_name, result_fields):
    """
    Function should parse Meta.required_fields from model recursively
    """
    assert get_required_fields(field_name, ModelWithMeta) == result_fields


def test_permission():
    """
    This decorator should create PermissionUser instance and pass it to decorated method
    and apply other decorators passed as parameter
    """
    def some_method(*args, **kwargs):
        return args, kwargs

    def some_decorator(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            return method(*args, some_decorator_mark=True, **kwargs)
        return wrapper

    request_type, many = 'test', 'many'
    new_method = permission(some_method, request_type=request_type, many=many, decorators=[some_decorator])

    result = new_method()
    # check that permission user passed to decorated method with params
    permission_user = result[1]['_permission_user']
    assert (permission_user.request_type, permission_user.many) == (request_type, many)

    # check that some_decorator applied
    assert result[1]['some_decorator_mark']


class TestPermissionPlugin:

    @pytest.fixture()
    def instance(self):
        return PermissionPlugin()

    @pytest.fixture()
    def strict_instance(self):
        return PermissionPlugin(strict=True)

    @pytest.fixture()
    def mock__permission_for_schema(self):
        with mock.patch.object(PermissionPlugin, '_permission_for_schema') as mocked:
            yield mocked

    @pytest.fixture()
    def resource_list(self):
        def custom_decorator_list(f):
            pass

        class SomeResourceList(ResourceList):
            decorators = (custom_decorator_list, )
            data_layer = {
                'session': None,
                'model': ModelWithMeta,
            }
        return SomeResourceList

    @pytest.fixture()
    def resource_detail(self):
        def custom_decorator_detail(f):
            pass

        class SomeResourceDetail(ResourceDetail):
            decorators = (custom_decorator_detail, )
            data_layer = {
                'session': None,
                'model': ModelWithMeta,
            }
        return SomeResourceDetail

    @pytest.fixture()
    def permission_user(self):
        return PermissionUser(request_type='get')

    @pytest.fixture()
    def sqlalchemy_data_layer(self, session, resource_detail):
        resource_detail.schema = ModelWithMetaSchema
        return SqlalchemyDataLayer(dict(session=session, model=ModelWithMeta, resource=resource_detail))

    @pytest.mark.parametrize('resource_class_type, methods', (
            ('list', ('get', 'post')),
            ('detail', ('get', 'patch', 'delete', 'post')),
    ))
    @mock.patch.object(PermissionPlugin, '_permission_method')
    def test_after_route(self, mock_permission_method, instance, resource_list, resource_detail, resource_class_type,
                         methods):
        resource_map = {'list': resource_list, 'detail': resource_detail}
        resource = resource_map[resource_class_type]
        instance.after_route(resource, self_json_api=JsonApi)
        assert mock_permission_method.call_count == len(methods)
        for i, args in enumerate(mock_permission_method.call_args_list):
            assert args[0][0] == resource
            assert args[0][1] == methods[i]
            assert args[0][2] == JsonApi
        assert resource._permission_plugin_inited

    @mock.patch.object(PermissionPlugin, '_permission_method')
    def test_after_route__already_inited(self, mock_permission_method, instance, resource_list, resource_detail):
        resource_list._permission_plugin_inited = resource_detail._permission_plugin_inited = True
        instance.after_route(resource_list)
        instance.after_route(resource_detail)
        mock_permission_method.assert_not_called()

    @pytest.mark.parametrize('many, methods', (
            (True, {'get': 'get_list', 'post': 'post'}),
            (False, {'get': 'get', 'patch': 'patch', 'delete': 'delete'}),
    ))
    @mock.patch('combojsonapi.permission.permission_plugin.permission')
    def test__permission_method(self, mock_permission, instance, resource_detail, resource_list, many, methods):
        resource_map = {True: resource_list, False: resource_detail}
        resource = resource_map[many]
        permission_list = [SomePermission]

        for method, permission_type in methods.items():
            old_method = getattr(resource, method)
            resource.data_layer[f'permission_{method}'] = permission_list
            instance._permission_method(resource, method, JsonApi)

            # check that permissions were added to PermissionToMapper
            assert getattr(PermissionToMapper, permission_type)[ModelWithMeta.__name__] == {
                'model': ModelWithMeta,
                'permission': permission_list,
            }

            # check that new method is decorated by "permission" decorator
            assert getattr(resource, method) == mock_permission.return_value
            # check permission decorator params
            assert mock_permission.call_args[0] == (old_method, )
            kwargs = mock_permission.call_args[1]
            assert kwargs['request_type'] == method
            assert kwargs['many'] == many
            assert kwargs['decorators'] == list(resource.decorators)

    @pytest.mark.parametrize('resource_class_type, methods', (
            ('list', {'get': 'get_list', 'post': 'post'}),
            ('detail', {'get': 'get', 'patch': 'patch', 'delete': 'delete'}),
    ))
    def test__permission_method__strict_checks_permissions_not_empty(self, strict_instance, resource_detail,
                                                                     resource_list, resource_class_type, methods):
        resource_map = {'list': resource_list, 'detail': resource_detail}
        resource = resource_map[resource_class_type]
        for method, permission_type in methods.items():
            with pytest.raises(PermissionException) as e:
                # strict class should raise exception if no permissions provided
                strict_instance._permission_method(resource, method, JsonApi)
            assert e.value.args[0] == f"No permission case for {ModelWithMeta.__name__} {permission_type}"

            resource.data_layer[f'permission_{method}'] = [SomePermission]
            # no exceptions because permissions for method were added
            strict_instance._permission_method(resource, method, JsonApi)

    @pytest.mark.parametrize('resource_class_type, methods', (
            ('list', ('get', 'post')),
            ('detail', ('get', 'patch', 'delete')),
    ))
    def test__permission_method__type_method_not_in_resource_methods(self, instance, resource_detail, resource_list,
                                                                     resource_class_type, methods):
        resource_list.methods = resource_detail.methods = []
        resource_map = {'list': resource_list, 'detail': resource_detail}
        resource = resource_map[resource_class_type]
        for method in methods:
            instance._permission_method(resource, method, JsonApi)
            assert getattr(resource, method) == instance._resource_method_bad_request

    def test__resource_method_bad_request(self):
        with pytest.raises(BadRequest) as e:
            PermissionPlugin._resource_method_bad_request()
        assert e.value.detail == 'No method'

    def test__permission_for_link_schema(self, permission_user):
        PermissionToMapper.add_permission('get', ModelWithMeta, [SomePermission])
        schema = ModelWithMetaSchema()
        PermissionPlugin._permission_for_link_schema(
            schema=schema, prefix_name_column='',
            columns=permission_user.permission_for_get(ModelWithMeta).columns_and_jsonb_columns
        )

        expected_fields = {'name', 'type', 'description', 'settings'}
        # check that only allowed fields are in schema now
        assert set(schema.fields.keys()) == set(schema.dump_fields.keys()) == set(schema.only) == expected_fields
        # check that func was applied recursively for nested schema
        settings_schema = schema.fields['settings'].schema
        assert set(settings_schema.fields.keys()) == set(settings_schema.dump_fields.keys()) == \
               set(settings_schema.only) == {'first_attr'}

    @mock.patch.object(PermissionPlugin, '_permission_for_link_schema')
    def test__permission_for_schema(self, mock__permission_for_link_schema, permission_user):
        schema, model = 'schema', ModelWithMeta
        PermissionToMapper.get.clear()
        PermissionPlugin._permission_for_schema(schema=schema, model=model, _permission_user=permission_user)
        mock__permission_for_link_schema.assert_called_once_with(
            schema=schema, prefix_name_column="", _permission_user=permission_user,
            columns={'id', 'name', 'type', 'flags', 'description', 'settings', 'related_model_id'},
        )

    def test__permission_for_schema__no_permission_user(self):
        with pytest.raises(Exception) as e:
            PermissionPlugin._permission_for_schema(schema='schema', model=ModelWithMeta)
        assert e.value.args[0] == 'No permission for user'

    @classmethod
    def get_args_and_kwargs(cls):
        return ('arg1', 'arg2'), {'schema': 'schema', 'model': 'model', 'kwarg1': 1, 'kwarg2': 2}

    def test_after_init_schema_in_resource_list_post(self, instance, mock__permission_for_schema):
        args, kwargs = self.get_args_and_kwargs()
        instance.after_init_schema_in_resource_list_post(*args, **kwargs)
        mock__permission_for_schema.assert_called_once_with(instance, *args, **kwargs)

    def test_after_init_schema_in_resource_list_get(self, instance, mock__permission_for_schema):
        args, kwargs = self.get_args_and_kwargs()
        instance.after_init_schema_in_resource_list_get(*args, **kwargs)
        mock__permission_for_schema.assert_called_once_with(instance, *args, **kwargs)

    def test_after_init_schema_in_resource_detail_get(self, instance, mock__permission_for_schema):
        args, kwargs = self.get_args_and_kwargs()
        instance.after_init_schema_in_resource_detail_get(*args, **kwargs)
        mock__permission_for_schema.assert_called_once_with(instance, *args, **kwargs)

    def test_after_init_schema_in_resource_detail_patch(self, instance, mock__permission_for_schema):
        args, kwargs = self.get_args_and_kwargs()
        instance.after_init_schema_in_resource_detail_patch(*args, **kwargs)
        mock__permission_for_schema.assert_called_once_with(instance, *args, **kwargs)

    def test_data_layer_create_object_clean_data(self, instance, resource_list):
        permission_user = mock.Mock()
        data = {'foo': 'bar'}
        join_fields = ['spam', 'eggs']
        view_kwargs = {'_permission_user': permission_user}
        self_json_api = resource_list._data_layer
        result = instance.data_layer_create_object_clean_data(data=data, view_kwargs=view_kwargs,
                                                              join_fields=join_fields, self_json_api=self_json_api)
        assert result == permission_user.permission_for_post_data.return_value
        permission_user.permission_for_post_data.assert_called_once_with(model=self_json_api.model, data=data,
                                                                         join_fields=join_fields, **view_kwargs)

    @mock.patch.object(PermissionPlugin, '_eagerload_includes', side_effect=lambda q, *_, **__: q)
    def test_data_layer_get_object_update_query(self, mock_eagerload_includes, instance, permission_user, session,
                                                sqlalchemy_data_layer):
        PermissionToMapper.add_permission('get', ModelWithMeta, [PermissionWithJoinsAndFilters])

        kwargs = dict(
            query=session.query(ModelWithMeta),
            qs=QueryStringManager({'fields[model_with_meta]': 'name,type,flags'}, ModelWithMetaSchema),
            self_json_api=sqlalchemy_data_layer,
            view_kwargs={'_permission_user': permission_user}
        )

        result = instance.data_layer_get_object_update_query(**kwargs)

        permission_get = permission_user.permission_for_get(ModelWithMeta)
        expected_query = str(
            session.query(ModelWithMeta)
            # check that joins and filters from permission were applied
                   .join(*permission_get.joins[0])
                   .filter(*permission_get.filters)
            # and only requested and allowed fields were selected
                   .with_entities(ModelWithMeta.id, ModelWithMeta.name, ModelWithMeta.type, ModelWithMeta.flags)
                   .statement)
        assert str(result.statement) == expected_query

    @mock.patch.object(PermissionPlugin, '_eagerload_includes', side_effect=lambda q, *_, **__: q)
    def test_data_layer_get_collection_update_query(self, mock_eagerload_includes, instance, permission_user, session,
                                                    sqlalchemy_data_layer):
        PermissionToMapper.add_permission('get', ModelWithMeta, [PermissionWithJoinsAndFilters])

        kwargs = dict(
            query=session.query(ModelWithMeta),
            qs=QueryStringManager({'fields[model_with_meta]': 'type,flags'}, ModelWithMetaSchema),
            self_json_api=sqlalchemy_data_layer,
            view_kwargs={'_permission_user': permission_user}
        )

        result = instance.data_layer_get_collection_update_query(**kwargs)

        permission_get = permission_user.permission_for_get(ModelWithMeta)
        expected_query = str(
            session.query(ModelWithMeta)
                # check that joins and filters from permission were applied
                .join(*permission_get.joins[0])
                .filter(*permission_get.filters)
                # and only requested and allowed fields were selected
                .with_entities(ModelWithMeta.id, ModelWithMeta.type)
                .statement)
        assert str(result.statement) == expected_query

    def test_data_layer_update_object_clean_data(self, instance, sqlalchemy_data_layer, permission_user):
        PermissionToMapper.add_permission('patch', ModelWithMeta, [SomePermission])
        data = {}
        result = instance.data_layer_update_object_clean_data(data=data, self_json_api=sqlalchemy_data_layer,
                                                              view_kwargs={'_permission_user': permission_user})
        assert result['patched_by_some_permission']

    def test_data_layer_delete_object_clean_data(self, instance, permission_user, sqlalchemy_data_layer):
        PermissionToMapper.add_permission('delete', ModelWithMeta, [SomePermission])
        obj = mock.Mock()
        obj.deletable = True

        # doesn't raise for deletable object
        instance.data_layer_delete_object_clean_data(obj=obj,
                                                     self_json_api=sqlalchemy_data_layer,
                                                     view_kwargs={'_permission_user': permission_user})

        obj.deletable = False
        with pytest.raises(JsonApiException) as e:
            instance.data_layer_delete_object_clean_data(obj=obj,
                                                         self_json_api=sqlalchemy_data_layer,
                                                         view_kwargs={'_permission_user': permission_user})
        assert e.value.detail == "It is forbidden to delete the object"

    def test__get_permission_user(self, permission_user):
        result = PermissionPlugin._get_permission_user({'_permission_user': permission_user})
        assert result is permission_user

    def test__get_permission_user__no_user(self):
        with pytest.raises(Exception) as e:
            PermissionPlugin._get_permission_user({})
        assert e.value.args[0] == "No permission for user"

    def test__get_model(self):
        result = PermissionPlugin._get_model(ModelWithMeta, 'related_model_id')
        assert result is RelatedModel

    def test__get_model__wrong_field(self):
        field = 'wrong_fk'
        with pytest.raises(ValueError) as e:
            PermissionPlugin._get_model(ModelWithMeta, field)
        assert e.value.args[0] == f"No foreign key {field} in mapper {ModelWithMeta.__name__}"

    @pytest.mark.parametrize('field_name, result', (
            pytest.param('description', True, id='allowed field'),
            pytest.param('flags', False, id='not allowed field'),
    ))
    def test__is_access_foreign_key(self, permission_user, field_name, result):
        PermissionToMapper.add_permission('get', ModelWithMeta, [SomePermission])
        assert result is PermissionPlugin._is_access_foreign_key(field_name, ModelWithMeta, permission_user)

    @pytest.mark.parametrize('qs, new_fields, new_include', (
            ({f'fields[{ModelWithMetaSchema.Meta.type_}]': 'name,type,flags',
              'include': 'related_model_id'},
             {'name', 'type'},
             'related_model_id'),
            ({f'fields[{ModelWithMetaSchema.Meta.type_}]': 'flags',
              'include': 'related_model_id'},
             {'flags'},  # TODO is it okay?
             ''),
    ))
    def test__update_qs_fields(self, permission_user, qs, new_fields, new_include):
        PermissionToMapper.add_permission('get', ModelWithMeta, [SomePermission])
        qs = QueryStringManager(qs,
                                ModelWithMetaSchema)
        PermissionPlugin._update_qs_fields(ModelWithMetaSchema.Meta.type_,
                                           list(permission_user.permission_for_get(ModelWithMeta).columns),
                                           qs,
                                           'related_model_id')
        assert set(qs.fields['model_with_meta']) == new_fields
        assert qs.qs['include'] == new_include

    @mock.patch.object(PermissionPlugin, '_update_qs_fields')
    def test__get_access_fields_in_schema(self, mock__update_qs_fields, permission_user):
        qs = QueryStringManager({}, ModelWithMetaSchema)
        expected_result = {'id', 'other_field'}
        result = PermissionPlugin._get_access_fields_in_schema('related_model_id', ModelWithMetaSchema, permission_user,
                                                               ModelWithMeta, qs=qs)
        assert set(result) == expected_result
        mock__update_qs_fields.assert_called_once()
        args, kwargs = mock__update_qs_fields.call_args[0], mock__update_qs_fields.call_args[1]
        assert args[0] == RelatedModelSchema.Meta.type_
        assert set(args[1]) == expected_result
        assert kwargs == {'qs': qs, 'name_foreign_key': 'related_model_id'}

    @pytest.mark.parametrize('relationship_schema', (
        'RelatedModelSchema', RelatedModelSchema(), RelatedModelSchema
    ))
    def test__get_schema(self, relationship_schema):
        field = 'related_model_id'
        schema = ModelWithMetaSchema()
        schema._declared_fields[field].__dict__['_Relationship__schema'] = relationship_schema
        result = PermissionPlugin._get_schema(schema, field)
        assert result is RelatedModelSchema

    @mock.patch.object(ModelWithMeta.related_model_id, 'property')
    def test__get_or_update_joinedload_object(self, mock_property, permission_user):
        mock_property.mapper = mock_mapper
        qs = QueryStringManager({}, ModelWithMeta)
        joinedload_object, related_schema = PermissionPlugin._get_or_update_joinedload_object(
            None, qs, permission_user, ModelWithMeta, ModelWithMetaSchema, 'related_model_id', 'related_model_id', 0
        )
        assert joinedload_object.path[0] == ModelWithMeta.related_model_id
        assert related_schema is RelatedModelSchema

    @mock.patch.object(ModelWithMeta.related_model_id, 'property')
    @mock.patch.object(PermissionPlugin, '_is_access_foreign_key', return_value=True)
    def test__get_joinedload_object_for_splitted_include(self, mock_is_access_foreign_key, mock_property, permission_user):
        qs = QueryStringManager({}, ModelWithMeta)

        result = PermissionPlugin._get_joinedload_object_for_splitted_include('related_model_id', qs, permission_user,
                                                                              ModelWithMetaSchema(), ModelWithMeta)
        assert result.path[0] == ModelWithMeta.related_model_id

    @mock.patch.object(PermissionPlugin, '_is_access_foreign_key', return_value=False)
    def test__get_joinedload_object_for_splitted_include__not_allowed(self, mock_is_access_foreign_key, permission_user):
        qs = QueryStringManager({}, ModelWithMeta)

        result = PermissionPlugin._get_joinedload_object_for_splitted_include('related_model_id', qs, permission_user,
                                                                              ModelWithMetaSchema(), ModelWithMeta)
        assert result is None

    def test__get_joinedload_object_for_splitted_include__wrong_field_name(self, permission_user):
        qs = QueryStringManager({}, ModelWithMeta)

        with pytest.raises(InvalidInclude):
            PermissionPlugin._get_joinedload_object_for_splitted_include('wrong_field', qs, permission_user,
                                                                         ModelWithMetaSchema(), ModelWithMeta)

    @mock.patch.object(ModelWithMeta.related_model_id, 'property')
    @mock.patch.object(PermissionPlugin, '_is_access_foreign_key', return_value=True)
    def test__get_joinedload_object_for_include(self, mock_is_access_foreign_key, mock_property, permission_user):
        qs = QueryStringManager({}, ModelWithMeta)

        result = PermissionPlugin._get_joinedload_object_for_include('related_model_id', qs, permission_user,
                                                                     ModelWithMetaSchema(), ModelWithMeta)
        assert result.path[0] == ModelWithMeta.related_model_id

    def test__get_joinedload_object_for_include__wrong_field_name(self, permission_user):
        qs = QueryStringManager({}, ModelWithMeta)

        with pytest.raises(InvalidInclude):
            PermissionPlugin._get_joinedload_object_for_include('wrong_field', qs, permission_user,
                                                                ModelWithMetaSchema(), ModelWithMeta)

    @mock.patch('flask_combo_jsonapi.querystring.current_app')
    def test__eagerload_includes__no_includes(self, mock_current_app, session, permission_user, sqlalchemy_data_layer):
        mock_current_app.config.get.return_value = None
        query = session.query(ModelWithMeta)
        qs = QueryStringManager({}, ModelWithMeta)
        result = PermissionPlugin._eagerload_includes(query, qs, permission_user, sqlalchemy_data_layer)
        assert result is query

    @mock.patch.object(PermissionPlugin, '_is_access_foreign_key', return_value=False)
    @mock.patch.object(PermissionPlugin, '_get_joinedload_object_for_include')
    @mock.patch('flask_combo_jsonapi.querystring.current_app')
    def test__eagerload_includes__with_not_allowed_includes(
            self, mock_current_app, mock_get_joinedload_object_for_include, mock_is_access_foreign_key, session,
            permission_user, sqlalchemy_data_layer
    ):
        mock_current_app.config.get.return_value = None
        query = session.query(ModelWithMeta)
        include = 'related_model_id'
        qs = QueryStringManager({'include': include}, ModelWithMeta)
        result = PermissionPlugin._eagerload_includes(query, qs, permission_user, sqlalchemy_data_layer)
        assert result is query
        mock_get_joinedload_object_for_include.assert_not_called()

    @mock.patch.object(PermissionPlugin, '_is_access_foreign_key', return_value=True)
    @mock.patch.object(PermissionPlugin, '_get_joinedload_object_for_include')
    @mock.patch('flask_combo_jsonapi.querystring.current_app')
    def test__eagerload_includes__with_includes(
            self, mock_current_app, mock_get_joinedload_object_for_include, mock_is_access_foreign_key,
            permission_user, sqlalchemy_data_layer
    ):
        mock_current_app.config.get.return_value = None
        query = mock.Mock()
        include = 'related_model_id'
        qs = QueryStringManager({'include': include}, ModelWithMeta)
        result = PermissionPlugin._eagerload_includes(query, qs, permission_user, sqlalchemy_data_layer)

        mock_get_joinedload_object_for_include.assert_called_once_with(include, qs, permission_user,
                                                                       ModelWithMetaSchema, ModelWithMeta)
        query.options.assert_called_once_with(mock_get_joinedload_object_for_include.return_value)
        assert result == query.options.return_value

    @mock.patch.object(PermissionPlugin, '_get_joinedload_object_for_splitted_include')
    @mock.patch('flask_combo_jsonapi.querystring.current_app')
    def test_eagerload_includes__with_splitted_includes(
            self, mock_current_app, mock_get_joinedload_object_for_splitted_include, permission_user,
            sqlalchemy_data_layer
    ):
        mock_current_app.config.get.return_value = None
        query = mock.Mock()
        include = 'foo.bar'
        qs = QueryStringManager({'include': include}, ModelWithMeta)
        result = PermissionPlugin._eagerload_includes(query, qs, permission_user, sqlalchemy_data_layer)

        mock_get_joinedload_object_for_splitted_include.assert_called_once_with(include, qs, permission_user,
                                                                                ModelWithMetaSchema, ModelWithMeta)
        query.options.assert_called_once_with(mock_get_joinedload_object_for_splitted_include.return_value)
        assert result == query.options.return_value
