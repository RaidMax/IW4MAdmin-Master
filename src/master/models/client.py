from datetime import datetime
from typing import Iterable, List

from master.models.message import Message
from master.models.meta import Meta
from master.models.penalty import Penalty


class Client:
    def __init__(self,
                 network_id: str,
                 registered_at: datetime,
                 updated_at: datetime,
                 trust_factor: int,
                 display_names: List[str],
                 ip_addresses: List[str],
                 penalties: List[Penalty] = None,
                 messages: Iterable[Message] = None,
                 meta: Iterable[Meta] = None):
        self.network_id = network_id
        self.registered_at = registered_at
        self.updated_at = updated_at
        self.trust_factor = trust_factor
        self.display_names = display_names or []
        self.ip_addresses = ip_addresses or []
        self.penalties = penalties or []
        self.messages = messages
        self.meta = meta

    def update_alias(self, display_name: str, ip_address: str) -> None:
        self.display_names.append(display_name)
        self.ip_addresses.append(ip_address)

        self.display_names = list(set(self.display_names))
        self.ip_addresses = list(set(self.ip_addresses))

    def add_penalty(self, model: Penalty):
        self.penalties.append(model)
