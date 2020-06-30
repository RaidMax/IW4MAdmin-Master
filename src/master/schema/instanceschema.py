from marshmallow import Schema, fields, post_load, validate
from master.models.instancemodel import InstanceModel
from master.schema.serverschema import ServerSchema

class InstanceSchema(Schema):
    id = fields.String(
        required=True
    )
    version = fields.Inferred(
    )
    servers = fields.Nested(
        ServerSchema,
        many=True,
        validate=validate.Length(min=0, max=32, error='invalid server count')
    )
    uptime = fields.Int(
        required=True,
        validate=validate.Range(min=0, max=2147483647, error='invalid uptime')
    )
    last_heartbeat = fields.Int(
        required=False
    )

    @post_load
    def make_instance(self, data, **kwargs):
        return InstanceModel(**data)

