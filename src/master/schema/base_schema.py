from marshmallow import fields, Schema


class BaseSchema(Schema):
    date_created = fields.DateTime()
    date_modified = fields.DateTime()
    is_active = fields.Bool()
