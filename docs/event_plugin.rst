.. _event_plugin:

Event Plugin
------------

**EventPlugin**:

1. Allows to create Event-driven API (RPC api - custom views on top of general views)
2. Integrates with **ApiSpecPlugin** to make RPC documentation which is displayed
   along-side with non-RPC documentation. Views are described in **yaml**.
3. integrates with **PermissionPlugin**, and view can access restrictions for every model.
   View is restricted with general decorators, which are set up when API gets initialized.

How to use
~~~~~~~~~~
To create an RPC API for a model, do the following:

1. Create a class from :code:`combojsonapi.event.resource.EventsResource`. We'll detail this later.
2. Resource manager gets an :code:`events` attribute. There, specify a class you've just created.
   If you use a :code:`ResourceDetail` manager, every RPC API will receive model id specified in the resource manager.

How plugin works
""""""""""""""""

After you create a class inherited from :code:`combojsonapi.event.resource.EventsResource`,
any method with name starting with :code:`event_` will be considered as a separate view.
Its URL view will be: :code:`.../<url of the resource manager, which RPC API method class is attached to>/<method name: event_...`.

There's a way to override url suffix, see :ref:`Event Plugin extra params<Event-Plugin-extra-params>`.


POST resources are created by default. You can make a GET resource,
if you start the method's name with :code:`event_get_`. :code:`event_post_` is supported too, which would make a POST resource, again.

There's a way to override method, see :ref:`Event Plugin extra params<Event-Plugin-extra-params>`.


**Other methods and attributes of the Event class won't be visible in a view.**

How to describe a view
""""""""""""""""""""""

1. Method :code:`event[_post|get]_<method name>` accepts the following params:
    * :code:`id: int` [optional] - model instance id, if this view's class is specified in :code:`ResourceDetail` resource manager.
    * :code:`_permission_user: PermissionUser = None` - permissions for logged in user (if **PermissionPlugin** is used)
    * :code:`*args`
    * :code:`**kwargs`
2. Describe answers in JSON API format.
3. Document the view in yaml in the method beginning, so **ApiSpecPlugin** could automatically populate the swagger page with event method description.


.. _Event-Plugin-extra-params:

Plugin extra params
~~~~~~~~~~~~~~~~~~~

Event resource can be changed via extra params. Accepted params:

* :code:`method` - view method - GET/POST/PUT/PATCH/DELETE
* :code:`url_suffix` - custom url suffix to override using method name


In this example a new view will be created. It will be :code:`PUT /user/{id}/update_online/`.
Without event extra it will be :code:`POST /user/{id}/event_update_user_online_status/`.


.. code:: python

    from flask import request
    from flask_combo_jsonapi import ResourceDetail
    from combojsonapi.event.resource import EventsResource


    class UserDetailEvents(EventsResource):
        def event_update_user_online_status(self, *args, **kwargs):
            # language=YAML
            """
            ---
            # some swagger description
            """
            result = some_custom_stuff_to_do(kwargs, request.json)
            return result

        event_update_user_online_status.extra = {
            "method": "PUT",
            "url_suffix": "update_online",
        }


    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        events = UserDetailEvents
        methods = []
        data_layer = {
            'session': db.session,
            'model': User,
        }


Plugin usage example
~~~~~~~~~~~~~~~~~~~~

We want to upload a user avatar. We'll also load **ApiSpecPlugin**, so we can see it in action.

.. code:: python

    import os
    from flask import Flask, request
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import Query, load_only, scoped_session
    from flask_combo_jsonapi.marshmallow_fields import Relationship
    from flask_combo_jsonapi import Api, ResourceList, ResourceDetail
    from flask_combo_jsonapi.plugin import BasePlugin
    from flask_combo_jsonapi.querystring import QueryStringManager
    from combojsonapi.event.resource import EventsResource
    from combojsonapi.event import EventPlugin
    from combojsonapi.spec import ApiSpecPlugin
    from marshmallow_jsonapi.flask import Schema
    from marshmallow_jsonapi import fields


    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ECHO'] = True
    db = SQLAlchemy(app)

    """Models description"""

    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        url_avatar = Column(String)
        password = Column(String)


    db.create_all()

    """Models' schemas"""

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
        url_avatar = fields.String()
        password = fields.String()

    """Resource managers description for API"""

    class UserResourceDetailEvents(EventsResource):
        def event_update_avatar(self, *args, id: int = None, **kwargs):
            # language=YAML
            """
            ---
            summary: Обновление аватарки пользователя
            tags:
            - User
            parameters:
            - in: path
              name: id
              required: True
              type: integer
              format: int32
              description: 'id пользователя'
            - in: formData
              name: new_avatar
              type: file
              description: Новая аватарка пользователя
            consumes:
            - application/json
            responses:
              200:
                description: Ничего не вернёт
            """
            user = User.query.filter(User.id == id).one_or_none()
            if user is None:
                raise AccessDenied('You can not work with the user')

            avatar = request.files.get('new_avatar')
            if avatar:
                if avatar:
                    filename = avatar.filename
                    avatar.save(os.path.join(filename))
                user.url_avatar = os.path.join(filename)
                db.session.commit()
            return 'success', 201

        def event_get_info(self, *args, **kwargs):
            return {'message': 'GET INFO'}

        def event_post_info(self, *args, **kwargs):
            data = request.json
            data.update(message='POST INFO')
            return data

    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        events = UserResourceDetailEvents
        methods = ['GET']
        data_layer = {
            'session': db.session,
            'model': User,
        }

    class UserResourceList(ResourceList):
        schema = UserSchema
        methods = ['GET', 'POST']
        data_layer = {
            'session': db.session,
            'model': User,
        }

    """Initializing the API"""

    app.config['OPENAPI_URL_PREFIX'] = '/api/swagger'
    app.config['OPENAPI_VERSION'] = '3.0.0'
    app.config['OPENAPI_SWAGGER_UI_PATH'] = '/'
    app.config['OPENAPI_SWAGGER_UI_VERSION'] = '3.45.0'

    api_spec_plugin = ApiSpecPlugin(
        app=app,
        # Declaring tags list with their descriptions, so API gets organized into groups. This is optional: when there's no tags,
        # api will be grouped automatically by type schemas names (type_)
        tags={
            'User': 'User API'
        }
    )

    api_json = Api(
        app,
        plugins=[
            api_spec_plugin,
            EventPlugin()
        ]
    )
    api_json.route(UserResourceDetail, 'user_detail', '/api/user/<int:id>/', tag='User')
    api_json.route(UserResourceList, 'user_list', '/api/user/', tag='User')


    if __name__ == '__main__':
        for i in range(10):
            u = User(name=f'name{i}', fullname=f'fullname{i}', email=f'email{i}', password=f'password{i}')
            db.session.add(u)
        db.session.commit()
        app.run(port='9999')
