from datetime import datetime
from uuid import UUID


class PenaltyRevokedModel(object):
    def __init__(self, client_network_id: str, instance_guid: UUID, activated_at: datetime):
        self.client_network_id = client_network_id
        self.instance_guid = instance_guid
        self.activated_at = activated_at

    def name(self):
        return '{instance}-{network_id}-{activated}'.format(instance=self.instance_guid,
                                                            network_id=self.client_network_id,
                                                            activated=self.activated_at.ctime())

    def __repr__(self):
        return '<PenaltyRevokedModel(network_id={id}, instance_guid={instance_guid})>'\
            .format(id=self.client_network_id, instance_guid=self.instance_guid)

    def __str__(self):
        return self.__repr__()
