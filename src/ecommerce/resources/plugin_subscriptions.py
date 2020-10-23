from flask import request
from flask_restful import Resource

from ecommerce.integrations.logic.customer_logic import CustomerLogic


class PluginSubscription(Resource):
    def __init__(self, customer_logic: CustomerLogic = None):
        self._customer_logic = customer_logic or CustomerLogic()

    def get(self):
        subscription_id = request.args.get('subscription_id')
        instance_id = request.args.get('instance_id')

        if subscription_id is None or instance_id is None:
            return {'content': 'subscription_id and instance_id are required'}, 400

        content_data = self._customer_logic.get_subscribed_content(subscription_id, instance_id)
        return content_data, 200
