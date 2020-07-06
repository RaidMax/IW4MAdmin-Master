import uuid


class Penalty:
    def __init__(self, instance_guid: uuid, game: str, reason: str):
        self.instance_guid = instance_guid
        self.game = game
        self.reason = reason
