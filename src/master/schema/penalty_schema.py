from marshmallow import fields, post_load

from master.models.penalty import Penalty
from master.schema.base_schema import BaseSchema


class PenaltySchema(BaseSchema):
    instance_guid = fields.UUID(required=True)
    game = fields.String(required=True)
    reason = fields.String(required=True)
    
    @post_load
    def make_instance(self, data, **kwargs):
        return Penalty(**data)
