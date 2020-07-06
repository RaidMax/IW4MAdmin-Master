import logging
from uuid import UUID
from flask_restful import Resource
from flask import request
from marshmallow import ValidationError

from master.logic.client import ClientLogic
from master.schema.events.penalty_submitted_schema import PenaltySubmittedSchema
from master.schema.events.penalty_revoked_schema import PenaltyRevokedSchema
from master.data.penalty import PenaltyData


class Penalty(Resource):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.penalty_data = PenaltyData()
        self.client_logic = ClientLogic()

    def post(self, network_id: str):
        try:
            self.logger.info('call to {route}'.format(route=request.full_path), extra={'payload': request.json})
            request.json['client_network_id'] = network_id
            penalty = PenaltySubmittedSchema().load(request.json)
            self.logger.info('parsed penalty created event {penalty_event}'.format(penalty_event=penalty))
            result = self.client_logic.on_penalty_created(penalty)
            if not result:
                return {'message': 'failed to handle penalty created event'}, 500
            elif not result['success']:
                return {'message': result['message']}, result['code']
        except ValidationError as err:
            self.logger.warning('penalty created event failed validation', extra={'errors': err.messages})
            return {'message': err.messages}, 400
        return {'message': 'penalty created'}, 201

    def delete(self, client_network_id: str, instance_guid: UUID):
        try:
            self.logger.info('call to {route}'.format(route=request.full_path))
            penalty = PenaltyRevokedSchema().load({'client_network_id': client_network_id,
                                                   'instance_guid': instance_guid})
            self.logger.info('parsed penalty revoked event {penalty_event}'.format(penalty_event=penalty))
            result = self.penalty_data.soft_delete(penalty)
            if not result:
                return {'message': 'failed to handle penalty revoked event'}, 500
        except ValidationError as err:
            self.logger.warning('penalty revoked event failed validation', extra={'errors': err.messages})
            return {'message': err.messages}, 400
        return {}, 204
