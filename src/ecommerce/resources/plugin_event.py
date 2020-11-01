from flask import request
from flask_restful import Resource

from ecommerce.integrations.logic.event_logic import EventLogic


class PluginEvent(Resource):
    def __init__(self, event_logic: EventLogic = None):
        self._event_logic = event_logic or EventLogic()

    def post(self):
        if request.is_json is False:
            return 'request body must be json', 400

        result = False
        payload = request.get_json()
        if payload['event_type'] == 'subscription_created':
            result = self._event_logic.on_subscription_created(payload)
        if payload['event_type'] == 'subscription_cancelled':
            result = self._event_logic.on_subscription_cancelled(payload)

        if result:
            return 'event processed', 200
        else:
            return 'error processing event', 500
