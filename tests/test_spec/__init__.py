from flask import Flask
from flask_combo_jsonapi import ResourceList, ResourceDetail
from marshmallow import Schema, fields
from sqlalchemy import Integer, Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from combojsonapi.utils import Relationship

Base = declarative_base()

engine = create_engine("sqlite:///:memory:")
session = sessionmaker(bind=engine)()


class RelatedModel(Base):
    __tablename__ = 'related_model'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class SomeModel(Base):
    __tablename__ = 'some_model'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(Integer)
    flags = Column(Integer)
    description = Column(String)
    settings = Column(String)
    related_model_id = Column(Integer)


class RelatedModelSchema(Schema):
    class Meta:
        model = RelatedModel
        type_ = 'related_model'
        filtering = True

    id = fields.Integer()
    name = fields.String()


class SomeSchema(Schema):
    class Meta:
        model = SomeModel
        type_ = 'some_schema'

    id = fields.Integer()
    name = fields.String()
    type = fields.Integer()
    flags = fields.Integer()
    description = fields.Integer()
    related_model_id = Relationship(nested=RelatedModelSchema, schema=RelatedModelSchema)


class SchemaReversedName(Schema):
    class Meta:
        model = SomeModel
        type_ = 'schema_reversed_name'

    id = fields.Integer(description='just id field')
    name = fields.String(description='just name field')
    array_field = fields.List(fields.Integer, description='just array field with integers')


class SomeResourceDetail(ResourceDetail):
    schema = SomeSchema
    data_layer = {
        'session': session,
        'model': SomeModel,
    }


class SomeResourceList(ResourceList):
    schema = SomeSchema
    data_layer = {
        'session': session,
        'model': SomeModel,
    }


app = Flask(__name__)
app.add_url_rule('/apispec/some_url', view_func=SomeResourceDetail.as_view('some_view123'))