from marshmallow import fields, validate, post_load

from master.models.events.client_connected_model import ClientConnectedModel
from master.schema.base_schema import BaseSchema


class ClientConnectedSchema(BaseSchema):
    network_id = fields.String(required=True, min=1, max=16)
    display_name = fields.String(required=True, min=3, max=24)
    ip_address = fields.String(required=True, validate=validate.Regexp(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'))

    @post_load
    def make_instance(self, data, **kwargs):
        return ClientConnectedModel(**data)
