from datetime import datetime
from master.data.provider import FireBaseProvider
from master.models.events.penalty_submitted_model import PenaltySubmittedModel
from master.models.events.penalty_revoked_model import PenaltyRevokedModel
from master.schema.events.penalty_submitted_schema import PenaltySubmittedSchema

PENALTY_RESOURCE = 'penalty'


class PenaltyData:
    def __init__(self):
        self.provider = FireBaseProvider()

    def put(self, model: PenaltySubmittedModel):
        model_dict = PenaltySubmittedSchema().dump(model)
        return self.provider.post(resource=PENALTY_RESOURCE, payload=model_dict)

    def soft_delete(self, model: PenaltyRevokedModel):
        return self.provider.soft_delete(resource=PENALTY_RESOURCE,
                                         active_flag={'is_active': False,
                                                      'date_modified': datetime.utcnow().isoformat()})
