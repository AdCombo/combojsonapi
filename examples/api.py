from flask import Flask
from marshmallow import pre_load

from combojsonapi.event import EventPlugin
from combojsonapi.utils import Relationship
from combojsonapi.spec import ApiSpecPlugin

from combojsonapi.permission.permission_system import (
    PermissionMixin,
    PermissionForGet,
    PermissionUser,
    PermissionForPatch,
)
from combojsonapi.permission import PermissionPlugin
from flask_combo_jsonapi import Api, ResourceDetail, ResourceList
from flask_sqlalchemy import SQLAlchemy
from marshmallow_jsonapi.flask import Schema
from marshmallow_jsonapi import fields

# Create the Flask application
app = Flask(__name__)
app.config["DEBUG"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
app.config["SQLALCHEMY_ECHO"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/api-example.db"
db = SQLAlchemy(app)

# swagger / openapi config
app.config["OPENAPI_URL_PREFIX"] = "/api/swagger"
app.config["OPENAPI_VERSION"] = "3.0.0"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/"
app.config["OPENAPI_SWAGGER_UI_VERSION"] = "3.45.0"


# Create models
class Person(db.Model):

    class Meta:
        required_fields = {
            # OPTIONAL BUT RECOMMENDED
            # when using sparse fields (`GET /persons?fields[person]=full_name,email`)
            # when serialising obj, property `full_name` will use fields `first_name` and `last_name`
            # and they will be loaded one by one
            # BUT IF YOU USE PERMISSION PLUGIN
            # you can fix it by declaring `required_fields`
            # in format {"field_name": ["dependant field one", "another dependant field"]}
            "full_name": ["first_name", "last_name"],
        }

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    email = db.Column(db.String)
    password = db.Column(db.String)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Computer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"))
    person = db.relationship("Person", backref=db.backref("computers"))


db.create_all()


# Create logical data abstraction (same as data storage for this first example)
class PersonSchema(Schema):
    class Meta:
        type_ = "person"
        self_view = "person_detail"
        self_view_kwargs = {"id": "<id>"}
        self_view_many = "person_list"

    id = fields.Integer(as_string=True, dump_only=True)
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)
    full_name = fields.String(required=True, dump_only=True)
    email = fields.Email(load_only=True)
    computers = Relationship(
        nested="ComputerSchema",
        schema="ComputerSchema",
        self_view="person_computers",
        self_view_kwargs={"id": "<id>"},
        related_view="computer_list",
        related_view_kwargs={"id": "<id>"},
        many=True,
        type_="computer",
    )

    @pre_load
    def remove_id_before_deserializing(self, data, **kwargs):
        """
        We don't want to allow editing ID on POST / PATCH

        Related issues:
        https://github.com/AdCombo/flask-combo-jsonapi/issues/34
        https://github.com/miLibris/flask-rest-jsonapi/issues/193
        """
        if "id" in data:
            del data["id"]
        return data


class ComputerSchema(Schema):
    class Meta:
        type_ = "computer"
        self_view = "computer_detail"
        self_view_kwargs = {"id": "<id>"}

    id = fields.Integer(as_string=True, dump_only=True)
    serial = fields.String(required=True)
    owner = Relationship(
        nested="PersonSchema",
        schema="PersonSchema",
        attribute="person",
        self_view="computer_person",
        self_view_kwargs={"id": "<id>"},
        related_view="person_detail",
        related_view_kwargs={"computer_id": "<id>"},
        type_="person",
    )

    @pre_load
    def remove_id_before_deserializing(self, data, **kwargs):
        """
        We don't want to allow editing ID on POST / PATCH

        Related issues:
        https://github.com/AdCombo/flask-combo-jsonapi/issues/34
        https://github.com/miLibris/flask-rest-jsonapi/issues/193
        """
        if "id" in data:
            del data["id"]
        return data


# create Permissions


class PersonsPermission(PermissionMixin):
    ALL_FIELDS = [
        "id",
        "first_name",
        "last_name",
        "full_name",
        "email",
    ]

    def get(self, *args, many=True, user_permission: PermissionUser = None, **kwargs) -> PermissionForGet:
        """Setting avatilable columns"""
        self.permission_for_get.allow_columns = (self.ALL_FIELDS, 10)
        return self.permission_for_get


# Create resource managers
class PersonList(ResourceList):
    schema = PersonSchema
    data_layer = {
        "session": db.session,
        "model": Person,
        "permission_get": [PersonsPermission],
    }


class PersonDetail(ResourceDetail):
    schema = PersonSchema
    data_layer = {
        "session": db.session,
        "model": Person,
        "permission_get": [PersonsPermission],
    }


class ComputerList(ResourceList):
    schema = ComputerSchema
    data_layer = {
        "session": db.session,
        "model": Computer,
    }


class ComputerDetail(ResourceDetail):
    schema = ComputerSchema
    data_layer = {
        "session": db.session,
        "model": Computer,
    }


api_spec_plugin = ApiSpecPlugin(
    app=app,
    # Declaring tags list with their descriptions, so API gets organized into groups.
    # This is optional: when there are no tags,
    # api will be grouped automatically by type schemas names (type_)
    tags={
        "Person": "Person API",
        "Computer": "Computer API",
    },
)


# Create endpoints
api = Api(
    app,
    plugins=[
        api_spec_plugin,
        PermissionPlugin(strict=False),
        EventPlugin(trailing_slash=False),
    ],
)

api.route(PersonList, "person_list", "/persons", tag="Person")
api.route(
    PersonDetail,
    "person_detail",
    "/persons/<int:id>",
    "/computers/<int:computer_id>/owner",
    tag="Person",
)
api.route(
    ComputerList,
    "computer_list",
    "/computers",
    "/persons/<int:id>/computers",
    tag="Computer",
)
api.route(ComputerDetail, "computer_detail", "/computers/<int:id>", tag="Computer")


if __name__ == "__main__":
    # Start application
    app.run(debug=True)
