import base64
import logging
from typing import Iterable

import requests

from ecommerce.encryption.encryption_helper import encrypt_data
from ecommerce.helpers import determine_content_type
from ecommerce.integrations.data.customer_data import CustomerData
from ecommerce.integrations.logic.access_logic import AccessLogic


class CustomerLogic:
    def __init__(self, customer_data: CustomerData = None, access_logic: AccessLogic = None):
        self._logger = logging.getLogger(__name__)
        self._customer_data = customer_data or CustomerData()
        self._access_logic = access_logic or AccessLogic()

    def get_subscribed_content(self, subscription_id: str, instance_id: str, client_ip: str = None) -> Iterable:
        """
        retrieves the subscription content for subscriber
        :param subscription_id: subscription identifier (customer email)
        :param instance_id: admin instance identifier
        :param client_ip: requesting IP (for sharing detection; hashed before storage)
        :return:
        """

        customer_subscriptions = self._customer_data.get_customer_content_urls_by_email(subscription_id)

        # Plugin ids this subscription covers — recorded for sharing detection. Derived here
        # (not via a second ChargeBee call) since we already have the content URLs in hand.
        plugin_ids = [self.plugin_id_from_url(item.content_url)
                      for item in customer_subscriptions if getattr(item, 'content_url', None)]

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

        # Best-effort sharing-detection record. Never let tracking break delivery.
        self._access_logic.record_access(subscription_id, instance_id, plugin_ids, client_ip)

        return [{
            'content': item.content,
            'type': determine_content_type(item.content_url)
        } for item in filter(lambda c: hasattr(c, 'content'), customer_subscriptions)]

    @staticmethod
    def plugin_id_from_url(content_url: str) -> str:
        """Extracts the plugin identifier from a content URL (strip query, path, extension),
        e.g. ".../ZombieStatsPremium.dll" -> "ZombieStatsPremium"."""
        name = content_url.split('?')[0].rstrip('/').split('/')[-1]
        for ext in ('.dll', '.js', '.cs'):
            if name.lower().endswith(ext):
                return name[: -len(ext)]
        return name
