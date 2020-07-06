from marshmallow import Schema, fields, post_load
from master.models.events.penalty_revoked_model import PenaltyRevokedModel


class PenaltyRevokedSchema(Schema):
    client_network_id = fields.String(min=1, max=16, required=True)
    instance_guid = fields.UUID(required=True)
    activated_at = fields.DateTime(required=True)

    @post_load
    def make_instance(self, data, **kwargs):
        return PenaltyRevokedModel(**data)
