from os import environ
from firebase import firebase
from requests import HTTPError

import logging


class FireBaseProvider:
    def __init__(self):
        self.data_source = firebase.FirebaseApplication(environ['IA_DATA_SOURCE_URL'])
        self.logger = logging.getLogger(__name__)

    def get(self, resource: str, name: str) -> dict:
        self.logger.info('getting date from provider at /{url} for {name}'.format(url=resource, name=name))
        try:
            result = self.data_source.get(url=resource, name=name)
            return result
        except HTTPError as http_error:
            self.logger.error('encountered error when getting data from provider',
                              extra={'resource': resource, 'name': name},
                              exc_info=http_error)

    def put(self, resource: str, name: str, payload: dict) -> dict:
        self.logger.info('putting data to provider at /{url}'.format(url=resource), extra=payload)
        try:
            result = self.data_source.put(url='/{url}'.format(url=resource), name=name, data=payload)
            return result
        except HTTPError as http_error:
            self.logger.error('encountered error when posting to provider', extra=payload, exc_info=http_error)

    def post(self, resource: str, payload: dict) -> dict:
        self.logger.info('posting data to provider at /{url}'.format(url=resource), extra=payload)
        try:
            result = self.data_source.post(url='/{url}'.format(url=resource), data=payload)
            return result
        except HTTPError as http_error:
            self.logger.error('encountered error when posting to provider', extra=payload, exc_info=http_error)

    def soft_delete(self, resource: str, name: str, active_flag: dict):
        self.logger.info('soft deleting data on provider at /{url}/{name}'.format(url=resource, name=name))
        try:
            result = self.data_source.patch(url=resource, name=name, data=active_flag)
            return result
        except HTTPError as http_error:
            self.logger.error('encountered error when soft deleting {name}'.format(name=name), exc_info=http_error)
