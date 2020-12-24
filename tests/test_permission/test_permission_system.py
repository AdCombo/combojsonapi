from copy import deepcopy
from unittest import mock

import pytest
from flask_combo_jsonapi import JsonApiException
from flask_combo_jsonapi.utils import SPLIT_REL
from sqlalchemy import Column, Integer, String

from combojsonapi.permission import PermissionFields, PermissionForGet, PermissionToMapper, PermissionUser, \
    PermissionMixin, PermissionForPost, PermissionForPatch
from tests.test_permission import Base

module_path = 'combojsonapi.permission'


class MyModel(Base):
    __tablename__ = 'no table'
    id = Column(Integer, primary_key=True)
    name = Column(String)


class TestPermissionToMapper:

    permissions = ['some permission', 'foo', 'bar']

    types = ['get', 'get_list', 'post', 'patch', 'delete']

    @pytest.mark.parametrize('type_', types)
    def test_add_permission_success(self, type_):
        PermissionToMapper.add_permission(type_, MyModel, self.permissions)
        assert getattr(PermissionToMapper, type_)[MyModel.__name__] == {'model': MyModel,
                                                                        'permission': self.permissions}
        getattr(PermissionToMapper, type_).clear()

    def test_add_permission__fail__wrong_type(self):
        with pytest.raises(AttributeError):
            PermissionToMapper.add_permission('wrong_type', MyModel, self.permissions)


class TestPermissionFields:

    PermissionsWithJSONB = [
        'id',
        'name',
        'settings.foo',
        'settings.bar',
        'settings.spam',
    ]

    @pytest.fixture()
    def instance(self):
        return PermissionFields()

    @pytest.fixture()
    def other_instance(self):
        return PermissionFields()

    @pytest.mark.parametrize('self_columns, value, updated_columns', (
        pytest.param({}, (['foo'], 1), {'foo': 1}, id='update empty columns'),
        pytest.param({'foo': 1}, (['bar'], 3), {'foo': 1, 'bar': 3}, id='add new columns'),
        pytest.param({'foo': 2}, (['foo'], 1), {'foo': 2}, id='dont update with lower weight'),
        pytest.param({'foo': 1, 'bar': 1}, (['foo'], 2), {'foo': 2, 'bar': 1}, id='update with higher weight'),
    ))
    def test__update_columns(self, self_columns, value, updated_columns):
        PermissionFields._update_columns(self_columns, value)
        assert self_columns == updated_columns

    def test_allow_columns(self):
        mock_self = mock.Mock()
        result = PermissionFields.allow_columns.fget(mock_self)
        assert result == mock_self._allow_columns

    def test_allow_columns_setter(self, instance):
        assert not instance.allow_columns

        values = [(['foo', 'bar'], 10), (['spam', 'eggs'], 5)]
        for value in values:
            instance.allow_columns = value
            assert instance.allow_columns == {name: value[1] for name in value[0]}

    def test_forbidden_columns(self):
        mock_self = mock.Mock()
        result = PermissionFields.forbidden_columns.fget(mock_self)
        assert result == mock_self._forbidden_columns

    def test_forbidden_columns_setter(self, instance):
        assert not instance.forbidden_columns

        values = [(['spam', 'eggs'], 5), (['foo', 'bar'], 10)]
        for value in values:
            instance.forbidden_columns = value
            assert instance.forbidden_columns == {name: value[1] for name in value[0]}

    def test_columns_for_jsonb(self, instance):
        instance.allow_columns = self.PermissionsWithJSONB, 5
        instance.forbidden_columns = [self.PermissionsWithJSONB[-1]], 10

        result = instance.columns_for_jsonb('settings')

        # 0 and 1 elements aren't jsonb, -1 element is forbidden
        assert result == [i.split(SPLIT_REL)[1] for i in self.PermissionsWithJSONB[2:-1]]

    def test_columns(self, instance):
        instance.allow_columns = self.PermissionsWithJSONB, 5
        instance.forbidden_columns = [self.PermissionsWithJSONB[0]], 10

        # the only allowed non-jsonb column
        assert instance.columns == {self.PermissionsWithJSONB[1]}

    def test_columns_and_jsonb_columns(self, instance):
        instance.allow_columns = self.PermissionsWithJSONB, 5
        instance.forbidden_columns = [self.PermissionsWithJSONB[0]], 10

        # all allowed columns
        assert instance.columns_and_jsonb_columns == set(self.PermissionsWithJSONB[1:])

    def test__add__(self, instance, other_instance):
        instance.allow_columns = self.PermissionsWithJSONB[:3], 5
        instance.forbidden_columns = self.PermissionsWithJSONB[:3], 10
        other_instance.allow_columns = self.PermissionsWithJSONB[2:], 10
        other_instance.forbidden_columns = self.PermissionsWithJSONB[2:], 5

        result = instance + other_instance
        assert result.allow_columns == {k: 5 if i < 2 else 10
                                        for i, k in enumerate(self.PermissionsWithJSONB)}
        assert result.forbidden_columns == {k: 10 if i < 3 else 5
                                            for i, k in enumerate(self.PermissionsWithJSONB)}

    def test__init__(self):
        instance = PermissionFields(allow_columns=['foo', 'bar'], forbidden_columns=['spam', 'eggs'], weight=1)
        assert instance.allow_columns == {'foo': 1, 'bar': 1}
        assert instance.forbidden_columns == {'spam': 1, 'eggs': 1}


class TestPermissionForGet:
    @mock.patch(f'{module_path}.PermissionFields.__init__', autospec=True)
    def test__init__(self, mock_super_init):
        filters, joins = ['foo'], ['bar']
        allow_columns, forbidden_columns, weight = ['spam'], ['eggs'], 10

        instance = PermissionForGet(allow_columns=allow_columns, forbidden_columns=forbidden_columns, weight=weight,
                                    filters=filters, joins=joins)
        assert instance.filters == filters
        assert instance.joins == joins
        mock_super_init.assert_called_once_with(instance, allow_columns=allow_columns,
                                                forbidden_columns=forbidden_columns, weight=weight)

    @mock.patch(f'{module_path}.PermissionFields.__add__', autospec=True)
    def test__add__(self, mock_super_add):
        filters = ['foo', 'bar']
        joins = ['spam', 'eggs']
        instance_one = PermissionForGet(filters=filters[:1], joins=joins[:1])
        instance_two = PermissionForGet(filters=filters[1:], joins=joins[1:])

        result = instance_one + instance_two
        assert result.filters == filters
        assert result.joins == joins
        mock_super_add.assert_called_once_with(instance_one, instance_two)


class TestPermissionUser:

    class NameOnlyPermission(PermissionMixin):
        def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs):
            self.permission_for_get.allow_columns = ['name'], 1
            self.permission_for_get.forbidden_columns = ['id'], 1
            return self.permission_for_get

        def post_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPost:
            self.permission_for_post.allow_columns = ['name'], 2
            self.permission_for_post.forbidden_columns = ['id'], 2
            return self.permission_for_post

        def patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch:
            self.permission_for_patch.allow_columns = ['name'], 3
            self.permission_for_patch.forbidden_columns = ['id'], 3
            return self.permission_for_patch

        def post_data(self, *args, data=None, user_permission: PermissionUser = None, **kwargs) -> dict:
            data.setdefault('name', 'post-placeholder')
            return data

        def patch_data(self, *args, data=None, user_permission: PermissionUser = None, **kwargs) -> dict:
            data.setdefault('name', 'patch-placeholder')
            return data

    class IdFieldPermission(PermissionMixin):
        def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs):
            self.permission_for_get.allow_columns = ['id'], 2
            return self.permission_for_get

        def post_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPost:
            self.permission_for_post.allow_columns = ['id'], 3
            return self.permission_for_post

        def patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch:
            self.permission_for_patch.allow_columns = ['id'], 4
            return self.permission_for_patch

        def post_data(self, *args, data=None, user_permission: PermissionUser = None, **kwargs) -> dict:
            if 'id' in data:
                data['id'] = int(data['id'])
            return data

        def patch_data(self, *args, data=None, obj=None, user_permission: PermissionUser = None, **kwargs) -> dict:
            if 'id' in data:
                data['id'] = str(data['id'])
            return data

    class DeletePermission(PermissionMixin):
        def delete(self, *args, obj=None, user_permission: PermissionUser = None, **kwargs) -> bool:
            return True

    class DontDeletePermission(PermissionMixin):
        def delete(self, *args, obj=None, user_permission: PermissionUser = None, **kwargs) -> bool:
            return False

    @pytest.fixture()
    def instance_get(self):
        return PermissionUser(request_type='get')

    @pytest.fixture()
    def instance_get_many(self):
        return PermissionUser(request_type='get', many=True)

    @pytest.fixture()
    def instance_post(self):
        return PermissionUser(request_type='post')

    @pytest.fixture()
    def instance_patch(self):
        return PermissionUser(request_type='patch')

    @pytest.fixture()
    def instance_delete(self):
        return PermissionUser(request_type='delete')

    @pytest.fixture()
    def clean_permission_to_mapper(self):
        model_name = MyModel.__name__
        PermissionToMapper.get.pop(model_name, None)
        PermissionToMapper.get_list.pop(model_name, None)
        PermissionToMapper.post.pop(model_name, None)
        PermissionToMapper.patch.pop(model_name, None)
        PermissionToMapper.delete.pop(model_name, None)

    def test_permission_for_get__no_permissions(self, instance_get, clean_permission_to_mapper):
        """
        If model is not in PermissionToMapper, all fields should be added to `allow_columns` property.
        """
        result = instance_get.permission_for_get(MyModel)
        assert isinstance(result, PermissionForGet)
        assert result.allow_columns == {'id': 0, 'name': 0}
        assert result.forbidden_columns == {}

    @pytest.mark.parametrize('permission_list, expected_allow_columns, expected_forbidden_columns', (
            pytest.param([NameOnlyPermission], {'name': 1}, {'id': 1}, id='one permission'),
            pytest.param([NameOnlyPermission, IdFieldPermission], {'name': 1, 'id': 2}, {'id': 1},
                         id='multiple permissions'),
    ))
    def test_permission_for_get__with_permissions(self, instance_get, permission_list, expected_allow_columns,
                                                  expected_forbidden_columns):
        PermissionToMapper.add_permission('get', MyModel, permission_list)
        result = instance_get.permission_for_get(MyModel)
        assert result.allow_columns == expected_allow_columns
        assert result.forbidden_columns == expected_forbidden_columns

    def test_permission_for_get__many__no_permissions(self, instance_get_many, clean_permission_to_mapper):
        """
        If model is not in PermissionToMapper, all fields should be added to `allow_columns` property.
        """
        result = instance_get_many.permission_for_get(MyModel)
        assert isinstance(result, PermissionForGet)
        assert result.allow_columns == {'id': 0, 'name': 0}
        assert result.forbidden_columns == {}

    @pytest.mark.parametrize('permission_list, expected_allow_columns, expected_forbidden_columns', (
        pytest.param([NameOnlyPermission], {'name': 1}, {'id': 1}, id='one permission'),
        pytest.param([NameOnlyPermission, IdFieldPermission], {'name': 1, 'id': 2}, {'id': 1},
                     id='multiple permissions'),
    ))
    def test_permission_for_get__many__with_permissions(self, instance_get_many, permission_list,
                                                        expected_allow_columns, expected_forbidden_columns):
        PermissionToMapper.add_permission('get_list', MyModel, permission_list)
        result = instance_get_many.permission_for_get(MyModel)
        assert result.allow_columns == expected_allow_columns
        assert result.forbidden_columns == expected_forbidden_columns

    def test_permission_for_post_permission__no_permissions(self, instance_post, clean_permission_to_mapper):
        result = instance_post.permission_for_post_permission(MyModel)
        assert isinstance(result, PermissionForPost)
        assert result.allow_columns == {'id': 0, 'name': 0}
        assert result.forbidden_columns == {}

    @pytest.mark.parametrize('permission_list, expected_allow_columns, expected_forbidden_columns', (
            pytest.param([NameOnlyPermission], {'name': 2}, {'id': 2}, id='one permission'),
            pytest.param([NameOnlyPermission, IdFieldPermission], {'name': 2, 'id': 3}, {'id': 2},
                         id='multiple permissions'),
    ))
    def test_permission_for_post_permission__with_permissions(self, instance_post, permission_list,
                                                              expected_allow_columns, expected_forbidden_columns):
        PermissionToMapper.add_permission('post', MyModel, permission_list)
        result = instance_post.permission_for_post_permission(MyModel)
        assert result.allow_columns == expected_allow_columns
        assert result.forbidden_columns == expected_forbidden_columns

    def test_permission_for_patch_permission__no_permissions(self, instance_patch, clean_permission_to_mapper):
        result = instance_patch.permission_for_patch_permission(MyModel)
        assert isinstance(result, PermissionForPatch)
        assert result.allow_columns == {'id': 0, 'name': 0}
        assert result.forbidden_columns == {}

    @pytest.mark.parametrize('permission_list, expected_allow_columns, expected_forbidden_columns', (
            pytest.param([NameOnlyPermission], {'name': 3}, {'id': 3}, id='one permission'),
            pytest.param([NameOnlyPermission, IdFieldPermission], {'name': 3, 'id': 4}, {'id': 3},
                         id='multiple permissions'),
    ))
    def test_permission_for_patch_permission__with_permissions(self, instance_patch, permission_list,
                                                               expected_allow_columns, expected_forbidden_columns):
        PermissionToMapper.add_permission('patch', MyModel, permission_list)
        result = instance_patch.permission_for_patch_permission(MyModel)
        assert result.allow_columns == expected_allow_columns
        assert result.forbidden_columns == expected_forbidden_columns

    @pytest.mark.parametrize('data', (
            {},
            {'name': 'test'},
            {'id': 1, 'name': 'test'}
    ))
    def test_permission_for_post_data__no_permissions(self, instance_post, clean_permission_to_mapper, data):
        result = instance_post.permission_for_post_data(model=MyModel, data=deepcopy(data))
        assert result == data

    @pytest.mark.parametrize('data, permission_list, expected_result', (
            pytest.param({}, [NameOnlyPermission], {'name': 'post-placeholder'}, id='process name: add placeholder'),
            pytest.param({'id': '123'}, [IdFieldPermission], {'id': 123}, id='process id: change id'),
            pytest.param({'id': '123', 'name': 'test'}, [NameOnlyPermission, IdFieldPermission],
                         {'id': 123, 'name': 'test'}, id='process all: change id'),
            pytest.param({'id': 123}, [NameOnlyPermission, IdFieldPermission],
                         {'id': 123, 'name': 'post-placeholder'}, id='process all: add name placeholder'),
            pytest.param({'id': 1, 'name': 'test'}, [NameOnlyPermission, IdFieldPermission],
                         {'id': 1, 'name': 'test'}, id='process all: do nothing')
    ))
    def test_permission_for_post_data__with_permissions(self, instance_post, data, permission_list, expected_result):
        PermissionToMapper.add_permission('post', MyModel, permission_list)
        result = instance_post.permission_for_post_data(model=MyModel, data=data)
        assert result == expected_result

    @pytest.mark.parametrize('data', (
            {},
            {'name': 'test'},
            {'id': 1, 'name': 'test'}
    ))
    def test_permission_for_patch_data__no_permissions(self, instance_patch, clean_permission_to_mapper, data):
        result = instance_patch.permission_for_patch_data(model=MyModel, data=deepcopy(data))
        assert result == data

    @pytest.mark.parametrize('data, permission_list, expected_result', (
            pytest.param({}, [NameOnlyPermission], {'name': 'patch-placeholder'}, id='process name: add placeholder'),
            pytest.param({'id': 123}, [IdFieldPermission], {'id': '123'}, id='process id: change id'),
            pytest.param({'id': 123, 'name': 'test'}, [NameOnlyPermission, IdFieldPermission],
                         {'id': '123', 'name': 'test'}, id='process all: change id'),
            pytest.param({'id': '123'}, [NameOnlyPermission, IdFieldPermission],
                         {'id': '123', 'name': 'patch-placeholder'}, id='process all: add name placeholder'),
            pytest.param({'id': '1', 'name': 'test'}, [NameOnlyPermission, IdFieldPermission],
                         {'id': '1', 'name': 'test'}, id='process all: do nothing')
    ))
    def test_permission_for_patch_data__with_permissions(self, instance_patch, data, permission_list, expected_result):
        PermissionToMapper.add_permission('patch', MyModel, permission_list)
        result = instance_patch.permission_for_patch_data(model=MyModel, data=data)
        assert result == expected_result

    @pytest.mark.parametrize('permission_list, expected_raise', (
        pytest.param([], False, id='no permissions: dont raise'),
        pytest.param([DeletePermission], False, id='Permission allows to delete'),
        pytest.param([DeletePermission, DontDeletePermission], True, id='1 of permissions forbids to delete'),
    ))
    def test_permission_for_delete(self, instance_delete, permission_list, expected_raise):
        PermissionToMapper.add_permission('delete', MyModel, permission_list)
        raised = False
        try:
            instance_delete.permission_for_delete(model=MyModel)
        except JsonApiException as e:
            raised = True
        assert raised is expected_raise
