from master.data.provider import FireBaseProvider
from master.models.client import Client
from master.schema.client_schema import ClientSchema

RESOURCE_NAME = 'client'


class ClientData:
    def __init__(self):
        self.provider = FireBaseProvider()

    def get(self, identifier: str) -> Client:
        result = self.provider.get(resource=RESOURCE_NAME, name=identifier)
        if result:
            return ClientSchema().load(result)

    def put(self, model: Client):
        payload = ClientSchema().dump(model)
        return self.provider.put(resource=RESOURCE_NAME, name=model.network_id, payload=payload)

