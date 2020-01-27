Using Plugins (`EN`_ | `RU`_)
-----------------------------

Attaching Plugins
~~~~~~~~~~~~~~~~~
Plugins are attached with JSON API initialization. Here's a sample of **EventPlugin** usage:


.. code:: python

    from flask import Flask
    from flask_rest_jsonapi import Api
    from combojsonapi.event import EventPlugin

    app = Flask(__name__)
    api_json = Api(
        app,
        plugins=[
            EventPlugin(),
        ]
    )

Plugins API
~~~~~~~~~~~
**Following hooks are available at plugin initialization**

:code:`before_init_plugin(self, *args, app=None, **kwargs) -> None`

    Fires before json_api initializes

    - :code:`app` - link to Flask instance object

:code:`after_init_plugin(self, *args, app=None, **kwargs) -> None`

    Fires after json_api initializes

    - :code:`app` - link to Flask instance object

:code:`before_route(self, resource: Union[ResourceList, ResourceDetail] = None, view=None, urls: Tuple[str] = None, self_json_api: Api = None, **kwargs) -> None:`

    Resource managers pre-parsing before routers are created

    - :code:`resource` - resource manager;
    - :code:`view` - resource manager name;
    - :code:`urls` - URLs list at which resource will be available;
    - :code:`self_json_api` - link to Api instance.

:code:`after_route(self, resource: Union[ResourceList, ResourceDetail] = None, view=None, urls: Tuple[str] = None, self_json_api: Api = None, **kwargs) -> None:`

    Resource managers post-parsing after routers are created

    - :code:`resource` - resource manager;
    - :code:`view` - resource manager name;
    - :code:`urls` - URLs list at which resource will be available;
    - :code:`self_json_api` - link to Api instance.

:code:`after_init_schema_in_resource_list_post(self, *args, schema=None, model=None, **kwargs) -> None`

    Called after marshmallow schema initialization in ResourceList.post

    - :code:`schema` - serialization/deserialization schema linked with the resource;
    - :code:`model` - model linked with the resource.

:code:`after_init_schema_in_resource_list_get(self, *args, schema=None, model=None, **kwargs) -> None`

    Called after marshmallow schema initialization in ResourceList.get

    - :code:`schema` - serialization/deserialization schema linked with the resource;
    - :code:`model` - model linked with the resource.

:code:`after_init_schema_in_resource_detail_get(self, *args, schema=None, model=None, **kwargs) -> None`

    Called after marshmallow schema initialization in ResourceDetail.get

    - :code:`schema` - serialization/deserialization schema linked with the resource;
    - :code:`model` - model linked with the resource.

:code:`after_init_schema_in_resource_detail_patch(self, *args, schema=None, model=None, **kwargs) -> None`

    Called after marshmallow schema initialization in ResourceDetail.patch

    - :code:`schema` - serialization/deserialization schema linked with the resource;
    - :code:`model` - model linked with the resource.

:code:`data_layer_before_create_object(self, *args, data=None, view_kwargs=None, self_json_api=None, **kwargs) -> None`

    Called after data deserialization and before forming a database request to create a new object

    - :code:`data` - deserialized data;
    - :code:`view_kwargs` - resource manager kwargs;
    - :code:`self_json_api` - link to Api instance.

:code:`data_layer_create_object_clean_data(self, *args, data: Dict = None, view_kwargs=None, join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict`

    Parses input data and returns parsed data set, from which a new object will be created.

    - :code:`Dict data` - deserialized unparsed data set;
    - :code:`view_kwargs` - resource manager kwargs;
    - :code:`List[str] join_fields` - fields which are linked to other models;
    - :code:`self_json_api` - link to Api instance.

:code:`data_layer_after_create_object(self, *args, data=None, view_kwargs=None, self_json_api=None, obj=None, **kwargs) -> None`

    Called after object creation but before saving it to the database.

    - :code:`Dict data` - data used to create the new object;
    - :code:`view_kwargs` - resource manager kwargs;
    - :code:`obj` - object created from data;
    - :code:`self_json_api` - link to Api instance.

:code:`data_layer_get_object_update_query(self, *args, query: Query = None, qs: QueryStringManager = None, view_kwargs=None, self_json_api=None, **kwargs) -> Query`

    Called during database query creation for updating a single object. Query can be patched here, if needed. Returns patched DB query.

    - :code:`Query query` - generated database query;
    - :code:`QueryStringManager qs` - query parameters list;
    - :code:`view_kwargs` - resource manager kwargs;
    - :code:`self_json_api` - link to Api instance.

:code:`data_layer_get_collection_update_query(self, *args, query: Query = None, qs: QueryStringManager = None, view_kwargs=None, self_json_api=None, **kwargs) -> Query`

    Called during database query creation for updating multiple objects. Query can be patched here, if needed. Returns patched DB query.

    - :code:`Query query` - generated database query;
    - :code:`QueryStringManager qs` - query parameters list;
    - :code:`view_kwargs` - resource manager kwargs;
    - :code:`self_json_api` - link to Api instance.

:code:`data_layer_update_object_clean_data(self, *args, data: Dict = None, obj=None, view_kwargs=None, join_fields: List[str] = None, self_json_api=None, **kwargs) -> Dict`

    Parses data for the object to be updated. Returns parsed data set.

    - :code:`Dict data` - data with which the object is to be updated;
    - :code:`obj` - object to be updated;
    - :code:`view_kwargs` - resource manager kwargs;
    - :code:`self_json_api` - link to Api instance.
    - :code:`List[str] join_fields` - fields which are linked to other models.

:code:`data_layer_delete_object_clean_data(self, *args, obj=None, view_kwargs=None, self_json_api=None, **kwargs) -> None`

    Called before deleting object from the database.

    - :code:`obj` - object to delete;
    - :code:`view_kwargs` - resource manager kwargs;
    - :code:`self_json_api` - link to Api instance.

:code:`before_data_layers_filtering_alchemy_nested_resolve(self, self_nested: Any) -> None`

    Called before filter is created in Nested.resolve.
    When returns None, :code:`resolve` continues executing; when returns any other value, :code:`resolve` exits, and the hook function result is passed further in the call stack.

    - :code:`self_nested` - :code:`Nested` instance.

:code:`before_data_layers_sorting_alchemy_nested_resolve(self, self_nested: Any) -> None`

    Called before sort is created in Nested.resolve.
    When returns None, :code:`resolve` continues executing; when returns any other value, :code:`resolve` exits, and the hook function result is passed further in the call stack.

    - :code:`self_nested` - :code:`Nested` instance.

Making a New Plugin Sample
~~~~~~~~~~~~~~~~~~~~~~~~~~
Let's take a look at sample implementation of a plugin that will return data from get requests to :code:`ResourceList`, :code:`ResourceDetail`
in a short or detailed view based on pre-set parameter :code:`format=short|full`

.. code:: python

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import Query, load_only, scoped_session
    from combojsonapi.utils import Relationship
    from flask_rest_jsonapi import Api, ResourceList, ResourceDetail
    from flask_rest_jsonapi.plugin import BasePlugin
    from flask_rest_jsonapi.querystring import QueryStringManager
    from marshmallow_jsonapi.flask import Schema
    from marshmallow_jsonapi import fields


    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ECHO'] = True
    db = SQLAlchemy(app)
    app.config['FLASK_DEBUG'] = 1


    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        password = Column(String)


    db.create_all()


    class UserSchema(Schema):
        class Meta:
            type_ = 'user'
            self_view = 'user_detail'
            self_view_kwargs = {'id': '<id>'}
            self_view_many = 'user_list'
            ordered = True

        id = fields.Integer(as_string=True)
        name = fields.String()
        fullname = fields.String()
        email = fields.String()
        password = fields.String()


    class UserResourceList(ResourceList):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name']
        }


    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        method = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
            'short_format': ['id', 'name']
        }


    class FormatPlugin(BasePlugin):

        def _update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                            view_kwargs=None, self_json_api=None, **kwargs) -> Query:
            all_fields = self_json_api.model.__mapper__.column_attrs.keys()
            short_format = self_json_api.short_format if hasattr(self_json_api, 'short_format') else all_fields
            full_format = self_json_api.full_format if hasattr(self_json_api, 'full_format') else all_fields
            fields = short_format if qs.qs.get('format') == 'short' else full_format

            query = self_json_api.session.query(*[getattr(self_json_api.model, name_field) for name_field in  fields])
            return query

        def data_layer_get_object_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                                view_kwargs=None, self_json_api=None, **kwargs) -> Query:
            return self._update_query(*args, query=query, qs=qs, view_kwargs=view_kwargs,
                                        self_json_api=self_json_api, **kwargs)

        def data_layer_get_collection_update_query(self, *args, query: Query = None, qs: QueryStringManager = None,
                                                    view_kwargs=None, self_json_api=None, **kwargs) -> Query:
            return self._update_query(*args, query=query, qs=qs, view_kwargs=view_kwargs,
                                        self_json_api=self_json_api, **kwargs)



    api_json = Api(
        app,
        plugins=[
            FormatPlugin(),
        ]
    )
    api_json.route(UserResourceList, 'user_list', '/api/user/')
    api_json.route(UserResourceDetail, 'user_detail', '/api/user/<int:id>/')


    if __name__ == '__main__':
        for i in range(10):
            u = User(name=f'name{i}', fullname=f'fullname{i}', email=f'email{i}', password=f'password{i}')
            db.session.add(u)
        db.session.commit()
        app.run(use_reloader=True)


.. _`EN`: https://github.com/AdCombo/combojsonapi/blob/master/docs/en/create_plugins.rst
.. _`RU`: https://github.com/AdCombo/combojsonapi/blob/master/docs/ru/create_plugins.rst