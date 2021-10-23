from marshmallow import Schema, fields, post_load, validate
from ..models.instancemodel import InstanceModel
from ..schema.serverschema import ServerSchema


class InstanceSchema(Schema):
    id = fields.String(
        required=True
    )
    version = fields.Inferred(
    )
    servers = fields.Nested(
        ServerSchema,
        many=True,
        validate=validate.Length(min=0, max=64, error='invalid server count')
    )
    uptime = fields.Int(
        required=True,
        validate=validate.Range(min=0, max=2147483647, error='invalid uptime')
    )
    last_heartbeat = fields.Int(
        required=False
    )
    ip_address = fields.String(required=False)
    webfront_url = fields.String(required=False, missing=None)

    @post_load
    def make_instance(self, data, **kwargs):
        return InstanceModel(**data)
