from marshmallow import Schema, fields


class SimpleSchema(Schema):

    id = fields.Integer()
    name = fields.String()
