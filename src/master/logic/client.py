from master.data.client import ClientData
from master.models.client import Client
from master.models.events.client_connected_model import ClientConnectedModel
from datetime import datetime

from master.models.events.penalty_submitted_model import PenaltySubmittedModel
from master.models.penalty import Penalty


class ClientLogic:
    def __init__(self):
        self.data = ClientData()

    def on_connect(self, model: ClientConnectedModel):
        client_model = self.data.get(identifier=model.network_id)
        if client_model is None:
            client_model = Client(network_id=model.network_id,
                                  registered_at=datetime.utcnow(),
                                  updated_at=datetime.utcnow(),
                                  trust_factor=0,
                                  display_names=[model.display_name],
                                  ip_addresses=[model.ip_address],
                                  penalties=[],
                                  messages=[],
                                  meta=[])
        else:
            client_model.update_alias(display_name=model.display_name, ip_address=model.ip_address)
        self.data.put(model=client_model)

    def on_penalty_created(self, model: PenaltySubmittedModel):
        client_model = self.data.get(identifier=model.client_network_id)
        if client_model:
            penalty = Penalty(instance_guid=model.instance_guid, game=model.game, reason=model.reason)
            client_model.add_penalty(penalty)
            self.data.put(client_model)
            return {'success': True, 'message': 'added penalty', 'code': 200}
        return {'success': False, 'message': 'client not found', 'code': 404}
