from master.models.base_model import BaseModel


class ClientConnectedModel(BaseModel):
    def __init__(self, network_id: str, display_name: str, ip_address: str):
        super().__init__()
        self.network_id = network_id
        self.display_name = display_name
        self.ip_address = ip_address
