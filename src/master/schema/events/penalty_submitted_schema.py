from marshmallow import fields, post_load, validate
from master.models.events.penalty_submitted_model import PenaltySubmittedModel
from master.schema.base_schema import BaseSchema


class PenaltySubmittedSchema(BaseSchema):
    client_network_id = fields.String(min=1, max=16, required=True)
    client_name = fields.String(required=True, min=3, max=24)
    ip_address = fields.String(required=True, validate=validate.Regexp(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'))
    penalty_type = fields.String(required=True, min=1, max=32)
    game = fields.String(required=True, min=1, max=8)
    instance_guid = fields.UUID(required=True)
    activated_at = fields.DateTime(required=True)
    reason = fields.String(required=True)
    meta = fields.Dict(required=True)

    @post_load
    def make_instance(self, data, **kwargs):
        return PenaltySubmittedModel(**data)
