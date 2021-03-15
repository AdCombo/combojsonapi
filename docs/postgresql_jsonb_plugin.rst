.. _postgresql_jsonb_plugin:

PostgreSqlJSONB plugin
----------------------

**PostgreSqlJSONB** plugins features:

1. Allows working with **JSONB** PostgreSql fields similarly to a regular model on the client side. **get** requests are filtered and ordered by first-level JSONB fields.
2. Integrates with **ApiSpecPlugin** in swagger for **get** requests (for ResourceList views). New fields are added:

    * :code:`filter[<JSONB field name in the model>.<upper level JSONB field>]` - simple filter;
    * :code:`filter = [{"name": "<JSONB field name in the model>.<upper level JSONB field>", "op": "eq", "val": "<значение>"}]` - in complex filters, we can request JSONB fields similarly to regular fields in the model.
    * :code:`sort=<JSONB field name in the model>.<upper level JSONB field>` - used as deep sort.
3. Integrates with **PermissionPlugin**, so you can use upper level JSONB fields in permission cases.

How to use
~~~~~~~~~~
To use the plugin in your schemas with JSONB fields do the following:

1. In schema, describe JSONB field (from model) as Nested, linking to a schema with upper level fields in model JSONB field.
2. JSONB schema with upper-level fields must be inherited from :code:`combojsonapi.postgresql_jsonb.schema.SchemaJSONB` class.

And you're done.

Plugin usage example
~~~~~~~~~~~~~~~~~~~~

Let's take a look at sample implementation of a plugin, where we store user settings in JSONB field. This sample requires a postgresql database connection.

.. code:: python

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.dialects.postgresql.json import JSONB
    from sqlalchemy.orm import Query, load_only, scoped_session
    from flask_combo_jsonapi.marshmallow_fields import Relationship
    from flask_combo_jsonapi import Api, ResourceList, ResourceDetail
    from flask_combo_jsonapi.querystring import QueryStringManager
    from combojsonapi.postgresql_jsonb.schema import SchemaJSONB
    from combojsonapi.postgresql_jsonb import PostgreSqlJSONB
    from combojsonapi.spec import ApiSpecPlugin
    from marshmallow_jsonapi.flask import Schema
    from marshmallow_jsonapi import fields


    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = '<подключение к Postgresql базе данных>'
    app.config['SQLALCHEMY_ECHO'] = True
    db = SQLAlchemy(app)

    """Models description"""

    class User(db.Model):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        name = Column(String)
        fullname = Column(String)
        email = Column(String)
        password = Column(String)
        settings = Column(JSONB)


    db.create_all()

    """Models' schemas description"""

    class SettingsSchema(SchemaJSONB):
        active = fields.Boolean()
        age = fields.Integer()

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
        settings = fields.Nested('SettingsSchema')

    """API resource managers description"""

    class UserResourceDetail(ResourceDetail):
        schema = UserSchema
        events = UserEventsForResourceDetail
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
    app.config['OPENAPI_SWAGGER_UI_PATH'] = '/'
    app.config['OPENAPI_SWAGGER_UI_VERSION'] = '3.22.0'

    api_spec_plagin = ApiSpecPlugin(
        app=app,
        # Declaring tags list with their descriptions, so API gets organized into groups. This is optional: when there's no tags,
        # api will be grouped automatically by type schemas names (type_)
        tags={
            'User': 'API для user'
        }
    )

    api_json = Api(
        app,
        plugins=[
            api_spec_plagin,
            EventPlugin(),
            PostgreSqlJSONB()
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


Requests example
~~~~~~~~~~~~~~~~

With views described in example above, we can use new filtering and ordering features.

Request all active users with a simple filter:

.. code::

    /api/user/?filter[settings.active]=True

Request all users aged 18 and up with a complex filter, ordered by age desc, then name:

.. code::

    /api/user/?filter=[{"name":"settings.age","op": "gt","val": "18"}]&sort=-settings.age,name
