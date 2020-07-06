import logging

from flask import request
from flask_restful import Resource
from marshmallow import ValidationError

from master.logic.client import ClientLogic
from master.schema.events.client_connected_schema import ClientConnectedSchema


class Client(Resource):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logic = ClientLogic()

    def put(self, event_type: str):
        self.logger.info('received client event at {url}'.format(url=request.url))
        if event_type == 'connect':
            return self._handle_connect()

    def _handle_connect(self):
        self.logger.info('handling connect event')
        try:
            connect_event = ClientConnectedSchema().load(request.json)
            self.logic.on_connect(connect_event)
        except ValidationError as err:
            self.logger.warning('client connect event failed validation', extra={'errors': err.messages})
            return {'message': err.messages}, 400
        return {'message': 'client connect event handled'}, 200
