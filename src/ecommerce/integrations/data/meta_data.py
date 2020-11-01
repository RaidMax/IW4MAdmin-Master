from os import environ

from box import Box
from firebase import Firebase
from requests import HTTPError

import logging


class MetaData:
    def __init__(self):
        self._data_source = Firebase(dict(databaseURL=environ['IA_DATA_SOURCE_URL'],
                                          apiKey=environ['IA_DATA_API_KEY'],
                                          authDomain=environ['IA_DATA_AUTH_DOMAIN'],
                                          storageBucket=environ['IA_DATA_STORAGE_BUCKET'])).database()
        self._logger = logging.getLogger(__name__)

    def get(self, resource: str, name: str) -> Box:
        self._logger.debug('getting data from provider at /{url} for {name}'.format(url=resource, name=name))
        try:
            result = self._data_source.child(resource).child(name).get()
            return Box(result.val())
        except HTTPError as http_error:
            self._logger.error('encountered error when getting data from provider',
                               extra={'resource': resource, 'name': name},
                               exc_info=http_error)

    def set(self, resource: str, name: str, payload: Box) -> Box:
        self._logger.debug('setting data to provider at /{url}'.format(url=resource), extra=payload)
        try:
            result = self._data_source.child(resource).child(name).set(payload)
            return result
        except HTTPError as http_error:
            self._logger.error('encountered error when posting to provider', extra=payload, exc_info=http_error)
