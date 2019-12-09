Permission (`EN`_ | `RU`_)
--------------------------

**Permission** plugin enables features:

1. Attach decorators to routers.
2. Restrict what data is returned on objects (GET method):
    * by attribute (they won't be requested from database unless mentioned specifically);
    * by rows;
    * by rows based on complex filters, e. g. accessible for users in a specific group, or group owner.
3. Pre-parsing (sanitizing) input data for patching (PATCH method) and creating objects (POST method).
4. Check if user can delete an object.


How to use
~~~~~~~~~~
To create a permission system:

1. Inherit a class from :code:`combojsonapi.permission.permission_system.PermissionMixin` (detailed  below).
2. In resource manager, specify which methods use this permissions class in :code:`data_layer`.
3. If you need to disable permission decorators for the resource, set the following attribute: :code:`disable_global_decorators`.
4. Shared permissions are applied automatically by
   :code:`permission_manager` https://flask-rest-jsonapi.readthedocs.io/en/latest/permission.html. To disable it, set :code:`disable_permission` attribute. Example:


.. code:: python

    class AuthResource(ResourceList):
        disable_permission = True
        disable_global_decorators = True
        ...


PermissionMixin class API
"""""""""""""""""""""""""

**Properties:**

:code:`permission_for_get: PermissionForGet`

    User permissions for GET method. Contains properties:

    * :code:`filters: List` - filters list to apply when requesting objects. E. g., it's possible to allow user to view his profile only, not anyone else's.
    * :code:`joins: List` - models list to join when requesting objects. E. g. allow a user to view users of group he is part of.
    * :code:`allow_columns: Dict[str, int]` - allowed model attributes and permission weight (more is higher priority), which is useful for managing more and less restrictive permissions.
    * :code:`forbidden_columns: Dict[str, int]` - forbidden model attributes and permission weight.
    * :code:`columns: Set[str]` - accessible model attributes after applying all permissions by weight in ascending order.

:code:`permission_for_patch: PermissionForPatch`

    User permissions for PATCH method. Contains properties:

    * :code:`allow_columns: Dict[str, int]` - allowed model attributes and permission weight (more is higher priority), which is useful for managing more and less restrictive permissions.
    * :code:`forbidden_columns: Dict[str, int]` - forbidden model attributes and permission weight.
    * :code:`columns: Set[str]` - accessible model attributes after applying all permissions by weight in ascending order.

:code:`permission_for_post: PermissionForPost`

    User permissions for POST method. Contains properties:

    * :code:`allow_columns: Dict[str, int]` - allowed model attributes and permission weight (more is higher priority), which is useful for managing more and less restrictive permissions.
    * :code:`forbidden_columns: Dict[str, int]` - forbidden model attributes and permission weight.
    * :code:`columns: Set[str]` - accessible model attributes after applying all permissions by weight in ascending order.


**Methods:**

:code:`get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet`

    GET method permissions for current user, described in PermissionForGet

    - :code:`bool many` - if model is requested via ResourceList (True) or ResourceDetail (False);
    - :code:`PermissionUser user_permission` - permissions for current logged in user; all permissions are available, including other models and methods (GET, POST, PATCH).

:code:`post_data(self, *args, data=None, user_permission: PermissionUser = None, **kwargs) -> Dict`

    Pre-parses input data according to permissions. Returns parsed data for the object being created.

    - :code:`Dict data` - unparsed data for the object being created;
    - :code:`PermissionUser user_permission` - permissions for current logged in user; all permissions are available, including other models and methods (GET, POST, PATCH).

:code:`post_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPost`

    POST method permissions for current user, described in PermissionForGet

    - :code:`PermissionUser user_permission` - permissions for current logged in user; all permissions are available, including other models and methods (GET, POST, PATCH).

:code:`patch_data(self, *args, data=None, obj=None, user_permission: PermissionUser = None, **kwargs) -> Dict`

    Pre-parses input data according to permissions. Returns parsed data for the object being updated.

    - :code:`Dict data` - input data validated according to marshmallow schema;
    - :code:`obj` - object being updated;
    - :code:`PermissionUser user_permission` - permissions for current logged in user; all permissions are available, including other models and methods (GET, POST, PATCH).

:code:`patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch`

    PATCH method permissions for current user, described in PermissionForGet

    - :code:`PermissionUser user_permission` - permissions for current logged in user; all permissions are available, including other models and methods (GET, POST, PATCH).

:code:`delete(self, *args, obj=None, user_permission: PermissionUser = None, **kwargs) -> bool`

    Permissions check if user is allowed to delete the :code:`obj` object. Object won't be deleted if any :code:`delete` method returns False.

    - :code:`obj` - object being deleted
    - :code:`PermissionUser user_permission` - permissions for current logged in user; all permissions are available, including other models and methods (GET, POST, PATCH).


Resource Manager Descriptions
"""""""""""""""""""""""""""""

In :code:`data_layer` section you can specify following permission types:

* :code:`permission_get: List` - list of classes, which :code:`get` method will be requested from;
* :code:`permission_post: List` - list of classes, which :code:`post_permission` and :code:`post_data` methods will be requested from;
* :code:`permission_patch: List` - list of classes, which :code:`patch_permission` and :code:`patch_data` methods will be requested from;
* :code:`permission_delete: List` - list of classes, which :code:`delete` method will be requested from;


Usage Sample
~~~~~~~~~~~~

:code:`model`

.. code:: python

    from enum import Enum

    class Role(Enum):
        admin = 1
        limited_user = 2
        user = 3
        block = 4


    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        password = Column(String)
        role = Column(Integer)

:code:`permission`

.. code:: python

    from combojsonapi.permission.permission_system import PermissionMixin, PermissionForGet, \
        PermissionUser, PermissionForPatch


    class PermissionListUser(PermissionMixin):
        ALL_FIELDS = self_json_api.model.__mapper__.column_attrs.keys()
        SHORT_INFO_USER = ['id', 'name']

        def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
            """Setting avatilable columns"""
            if current_user.role == Role.admin.value:
                self.permission_for_get.allow_columns = (self.ALL_FIELDS, 10)
            elif current_user.role in [Role.limited_user.value, Role.user.value]:
                # limit attributes and forbid to view blocked users
                self.permission_for_get.allow_columns = (self.SHORT_INFO_USER, 0)
                self.permission_for_get.filters.append(User.role != Role.block.value)
            return self.permission_for_get

    class PermissionDetailUser(PermissionMixin):
        ALL_FIELDS = self_json_api.model.__mapper__.column_attrs.keys()
        AVAILABLE_FIELDS_FOR_PATCH = ['password']

        def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
            """Setting avatilable columns"""
            if current_user.role in [Role.limited_user.value, Role.user.value]:
                # only current user is allowed to be requested
                self.permission_for_get.filters.append(User.id != current_user.id)
            return self.permission_for_get

        def patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch:
            """Only password change is allowed"""
            self.permission_for_patch.allow_columns = (self.AVAILABLE_FIELDS_FOR_PATCH, 0)
            return self.permission_for_patch

        def patch_data(self, *args, data: Dict = None, obj: User = None, user_permission: PermissionUser = None, **kwargs) -> Dict:
            # password
            password = data.get('password')
            if password is not None:
                return {'password': hashlib.md5(password.encode()).hexdigest()}
            return {}

    class PermissionPatchAdminUser(PermissionMixin):
        """Allow admin user to change any field"""
        ALL_FIELDS = self_json_api.model.__mapper__.column_attrs.keys()

        def patch_permission(self, *args, user_permission: PermissionUser = None, **kwargs) -> PermissionForPatch:
            """Only password change is allowed"""
            if current_user.role == Role.admin.value:
                self.permission_for_patch.allow_columns = (self.ALL_FIELDS, 10)  # задаём вес 10, это будет более приоритетно
            return self.permission_for_patch

        def patch_data(self, *args, data: Dict = None, obj: User = None, user_permission: PermissionUser = None, **kwargs) -> Dict:
            if current_user.role == Role.admin.value:
                password = data.get('password')
                if password is not None:
                    data['password'] = hashlib.md5(password.encode()).hexdigest()
                return data
            return {}

:code:`views`

.. code:: python

    class UserResourceList(ResourceList):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name'],
            'permission_get': [PermissionListUser],
        }


    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name'],
            'permission_get': [PermissionDetailUser],
            'permission_patch': [PermissionDetailUser, PermissionPatchAdminUser],
        }

:code:`__init__`

.. code:: python

    api_json = Api(
        app,
        decorators=(login_required,),
        plugins=[
            PermissionPlugin(),
        ]
    )

.. _`EN`: https://github.com/AdCombo/ComboJSONAPI/docs/en/permission_plugin.rst
.. _`RU`: https://github.com/AdCombo/ComboJSONAPI/docs/ru/permission_plugin.rst