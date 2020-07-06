from marshmallow import fields, post_load

from master.schema.base_schema import BaseSchema
from master.schema.message_schema import MessageSchema
from master.schema.meta_schema import MetaSchema
from master.schema.penalty_schema import PenaltySchema
from master.models.client import Client


class ClientSchema(BaseSchema):
    network_id = fields.String(min=1, max=16, required=True)
    registered_at = fields.Date(required=True)
    updated_at = fields.Date(required=True)
    trust_factor = fields.Int(required=True)
    display_names = fields.List(fields.String, default=[])
    ip_addresses = fields.List(fields.String, default=[])
    penalties = fields.Nested(PenaltySchema, many=True, default=[])
    messages = fields.Nested(MessageSchema, many=True, default=[])
    meta = fields.Nested(MetaSchema, many=True, default=[])

    @post_load
    def make_instance(self, data, **kwargs):
        return Client(**data)
