from pathlib import Path

from flask import Flask
from flask_combo_jsonapi.exceptions import ObjectNotFound, BadRequest
from marshmallow import pre_load

from combojsonapi.event import EventPlugin
from combojsonapi.event.resource import EventsResource
from combojsonapi.spec import ApiSpecPlugin

from flask import request
from flask_combo_jsonapi import Api, ResourceDetail, ResourceList
from flask_sqlalchemy import SQLAlchemy
from marshmallow_jsonapi.flask import Schema
from marshmallow_jsonapi import fields


CURRENT_DIR = Path(__file__).resolve().parent
UPLOADS_DIR_NAME = Path("uploads")
UPLOADS_DIR = CURRENT_DIR / UPLOADS_DIR_NAME
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Create the Flask application
app = Flask(__name__)
app.config["DEBUG"] = True


# Initialize SQLAlchemy
app.config["SQLALCHEMY_ECHO"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/api-events-example.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# swagger / openapi config
app.config["OPENAPI_URL_PREFIX"] = "/api/swagger"
app.config["OPENAPI_VERSION"] = "3.0.0"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/"
app.config["OPENAPI_SWAGGER_UI_VERSION"] = "3.45.0"


# Create models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    username = db.Column(db.String)
    email = db.Column(db.String)
    avatar_path = db.Column(db.String)


db.create_all()


# Create logical data abstraction (same as data storage for this first example)
class UserSchema(Schema):
    class Meta:
        type_ = "user"
        self_view = "user_detail"
        self_view_kwargs = {"id": "<id>"}
        self_view_many = "user_list"

    id = fields.Integer(as_string=True, dump_only=True)
    name = fields.String(required=False)
    username = fields.String(required=True)
    email = fields.String(required=True)
    avatar_path = fields.String(required=False, dump_only=True)

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


# Create events


class UserResourceListEvents(EventsResource):
    def event_get_info(self, *args, **kwargs):
        return {"message": "some info"}

    def event_post_info(self, *args, **kwargs):
        data = request.json
        data.update(message="POST request info")
        return data


class UserResourceDetailEvents(EventsResource):

    def event_update_avatar(self, *args, id: int = None, **view_kwargs):
        # language=YAML
        """
        ---
        summary: Update user's avatar
        tags:
        - User
        parameters:
        - in: path
          name: id
          required: True
          type: integer
          format: int32
          description: "user's id"
        requestBody:
          content:
            multipart/form-data:
              schema:
                type: object
                properties:
                  new_avatar:
                    type: string
                    format: binary
        consumes:
        - multipart/form-data
        responses:
          201:
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    avatar_url:
                      type: string
                      example: "uploads/avatar.gif"
        """
        avatar = request.files.get("new_avatar")
        if not avatar:
            raise BadRequest("avatar file is required! please fill `new_avatar` form field")

        user = User.query.filter_by(id=id).one_or_none()
        if user is None:
            raise ObjectNotFound(
                "User #{} not found".format(id),
                source={"parameter": "id"},
            )

        filename = avatar.filename
        avatar_path = str(UPLOADS_DIR / filename)
        avatar.save(avatar_path)
        user.avatar_path = str(UPLOADS_DIR_NAME / filename)
        db.session.commit()
        return {"avatar_url": user.avatar_path}, 201

    event_update_avatar.extra = {
        "url_suffix": "update_avatar",
    }


# Create resource managers


class UserList(ResourceList):
    schema = UserSchema
    events = UserResourceListEvents
    data_layer = {
        "session": db.session,
        "model": User,
    }


class UserDetail(ResourceDetail):
    schema = UserSchema
    events = UserResourceDetailEvents
    data_layer = {
        "session": db.session,
        "model": User,
    }


api_spec_plugin = ApiSpecPlugin(
    app=app,
    # Declaring tags list with their descriptions, so API gets organized into groups.
    # This is optional: when there are no tags,
    # api will be grouped automatically by type schemas names (type_)
    tags={
        "User": "User API",
    },
)


# Create endpoints
api = Api(
    app,
    plugins=[
        api_spec_plugin,
        EventPlugin(trailing_slash=False),
    ],
)

api.route(UserList, "user_list", "/users", tag="User")
api.route(UserDetail, "user_detail", "/users/<int:id>", tag="User")


if __name__ == "__main__":
    # Start application
    app.run(debug=True)
