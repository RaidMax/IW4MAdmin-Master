"""
Persistence for subscription-access tracking (Tier 1.5: account-sharing detection).

Mirrors the existing MetaData Firebase wiring so it reuses the ecommerce app's data
provider with no new infrastructure. Records live under:
    subscription_access/{email_hash}/{instance_id} = {first_seen, last_seen, count, ip_hash}

email_hash is a keyed HMAC (see AccessLogic) — raw emails are never stored here.

NOTE (RaidMax): if you prefer SQL aggregation over Firebase, swap this class for a
psycopg2-backed implementation against the master Postgres (the ecommerce app would then
need DB connectivity, which it currently lacks). The logic layer is storage-agnostic.
"""

import logging
from os import environ

from firebase import Firebase


class AccessData:
    _RESOURCE = 'subscription_access'

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._data_source = Firebase(dict(databaseURL=environ['IA_DATA_SOURCE_URL'],
                                          apiKey=environ['IA_DATA_API_KEY'],
                                          authDomain=environ['IA_DATA_AUTH_DOMAIN'],
                                          storageBucket=environ['IA_DATA_STORAGE_BUCKET'])).database()

    def get_record(self, email_hash: str, instance_id: str):
        try:
            return self._data_source.child(self._RESOURCE).child(email_hash).child(instance_id).get().val()
        except Exception as ex:
            self._logger.error('could not read subscription access record', exc_info=ex)
            return None

    def set_record(self, email_hash: str, instance_id: str, payload: dict) -> None:
        try:
            self._data_source.child(self._RESOURCE).child(email_hash).child(instance_id).set(payload)
        except Exception as ex:
            self._logger.error('could not write subscription access record', exc_info=ex)

    def get_all(self) -> dict:
        try:
            return self._data_source.child(self._RESOURCE).get().val() or {}
        except Exception as ex:
            self._logger.error('could not read subscription access table', exc_info=ex)
            return {}
