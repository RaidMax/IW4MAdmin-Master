from os import environ

from flask import request
from flask_restful import Resource
import base64

from ecommerce.integrations.logic.customer_logic import CustomerLogic
from ecommerce.encryption.encryption_helper import encrypt_data


class PluginSubscription(Resource):
    def __init__(self, customer_logic: CustomerLogic = None):
        self._customer_logic = customer_logic or CustomerLogic()
        self._content_path = environ.get('ECOMMERCE_CONTENT_PATH', '')

    def get(self):
        subscription_id = request.args.get('subscription_id')
        instance_id = request.args.get('instance_id')

        if subscription_id is None or instance_id is None:
            return {'content': 'subscription_id and instance_id are required'}, 400

        # Disabled: special-case subscription handling
        # if subscription_id == 'nocody' and self._content_path:
        #     with open(f'{self._content_path}/Server.dll', mode='rb') as file:
        #         fileContent = file.read()
        #         encrypted_data = encrypt_data('Server.B2022Main'.encode() + fileContent, subscription_id, instance_id)
        #         content = base64.b64encode(encrypted_data).decode('utf-8')
        #         return content
        # if subscription_id == 'nocodyv2' and self._content_path:
        #     with open(f'{self._content_path}/AimML.Core.dll', mode='rb') as file:
        #         fileContent = file.read()
        #         encrypted_data = encrypt_data('Server.B2022Main'.encode() + fileContent, subscription_id, instance_id)
        #         content = base64.b64encode(encrypted_data).decode('utf-8')
        #         return content

        content_data = self._customer_logic.get_subscribed_content(subscription_id, instance_id)
        return content_data, 200
