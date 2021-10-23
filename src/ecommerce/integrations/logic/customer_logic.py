import base64
import logging
from typing import Iterable

import requests

from ecommerce.encryption.encryption_helper import encrypt_data
from ecommerce.helpers import determine_content_type
from ecommerce.integrations.data.customer_data import CustomerData


class CustomerLogic:
    def __init__(self, customer_data: CustomerData = None):
        self._logger = logging.getLogger(__name__)
        self._customer_data = customer_data or CustomerData()

    def get_subscribed_content(self, subscription_id: str, instance_id: str) -> Iterable:
        """
        retrieves the subscription content for subscriber
        :param subscription_id: subscription identifier
        :param instance_id: admin instance identifier
        :return:
        """
        customer_subscriptions = self._customer_data.get_customer_content_urls_by_email(subscription_id)
        for item in customer_subscriptions:
            try:
                response = requests.get(item.content_url)
                response.raise_for_status()
            except requests.RequestException as ex:
                self._logger.error(f'could not retrieve content at {item.content_url}', exc_info=ex)
                continue

            binary = response.content
            encrypted_data = encrypt_data(binary, subscription_id, instance_id)
            item.content = base64.b64encode(encrypted_data).decode('utf-8')

        return [{
            'content': item.content,
            'type': determine_content_type(item.content_url)
        } for item in filter(lambda c: hasattr(c, 'content'), customer_subscriptions)]
