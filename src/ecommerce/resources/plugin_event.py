from os import environ

from flask import request
from flask_restful import Resource
from datetime import datetime

from ecommerce.integrations.logic.event_logic import EventLogic


class PluginEvent(Resource):
    def __init__(self, event_logic: EventLogic = None):
        self._event_logic = event_logic or EventLogic()
        self._log_path = environ.get('ECOMMERCE_LOG_PATH')

    def post(self):
        if not request.is_json:
            return 'request body must be json', 400

        result = False
        payload = request.get_json()
        if payload['event_type'] == 'subscription_created':
            result = self._event_logic.on_subscription_created(payload)
        if payload['event_type'] == 'subscription_cancelled':
            result = self._event_logic.on_subscription_cancelled(payload)
        # Disabled: stateChanged logging
        # if payload['event_type'] == 'stateChanged' and self._log_path:
        #     now = datetime.now()
        #     with open(self._log_path, 'a') as f:
        #         f.write(now.isoformat() + '     (' + request.remote_addr + ','  + request.headers.get('CF-Connecting-IP') + ') : ' + payload['state'] + ' : ' + payload['file'] + '\n')

        if result:
            return 'event processed', 200
        else:
            return 'error processing event', 500
