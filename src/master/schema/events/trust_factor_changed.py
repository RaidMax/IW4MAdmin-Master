from marshmallow import fields
from master.schema.base_schema import BaseSchema


class TrustFactorChanged(BaseSchema):
    client_network_id = fields.String(min=1, max=16, required=True)
    instance_guid = fields.UUID(required=True)
