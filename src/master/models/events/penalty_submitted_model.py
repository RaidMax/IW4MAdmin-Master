from uuid import UUID
from datetime import datetime
from master.models.base_model import BaseModel


class PenaltySubmittedModel(BaseModel):
    def __init__(self, client_network_id: str, client_name: str, ip_address: str, penalty_type: str, game: str,
                 instance_guid: UUID, activated_at: datetime, reason: str, meta: dict):
        super().__init__()
        self.client_network_id = client_network_id
        self.client_name = client_name
        self.ip_address = ip_address
        self.penalty_type = penalty_type
        self.game = game
        self.instance_guid = instance_guid
        self.activated_at = activated_at
        self.reason = reason
        self.meta = meta

    def name(self):
        return '{instance}-{network_id}-{activated}'.format(instance=self.instance_guid,
                                                            network_id=self.client_network_id,
                                                            activated=self.activated_at.isoformat())

    def __repr__(self):
        return '<PenaltyCreatedModel(name={name}, network_id={client_network_id}, meta_count={meta_count})>'\
            .format(name=self.client_name, client_network_id=self.client_network_id, meta_count=len(self.meta))

    def __str__(self):
        return self.__repr__()
