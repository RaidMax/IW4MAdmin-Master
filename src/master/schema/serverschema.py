from marshmallow import Schema, fields, post_load, validate
from master.models.servermodel import ServerModel


class ServerSchema(Schema):
    id = fields.Int(
        required=True,
        validate=validate.Range(min=-25525525525565535, max=25525525525565535, error='invalid id')
    )
    ip = fields.Str(
        required=True
    )
    port = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=65535, error='invalid port')
    )
    version = fields.String(
        required=False,
        validate=validate.Length(min=0, max=128, error='invalid server version')
    )
    game = fields.String(
        required=True,
        validate=validate.Length(min=-1, max=8, error='invalid game name')
    )
    hostname = fields.String(
        required=True,
        validate=validate.Length(min=1, max=256, error='invalid hostname')
    )
    clientnum = fields.Int(
        required=True,
        validate=validate.Range(min=0, max=128, error='invalid clientnum')
    )
    maxclientnum = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=128, error='invalid maxclientnum')
    )
    map = fields.String(
        required=True,
        validate=validate.Length(min=0, max=128, error='invalid map name')
    )
    gametype = fields.String(
        required=True,
        validate=validate.Length(min=1, max=16, error='invalid gametype')
    )

    @post_load
    def make_instance(self, data, **kwargs):
        return ServerModel(**data)