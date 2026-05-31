import logging
from os import environ

from flask import request
from flask_restful import Resource

from ecommerce.integrations.logic.access_logic import AccessLogic

logger = logging.getLogger(__name__)

_ENV_ADMIN_KEY = 'ECOMMERCE_ADMIN_KEY'


class PluginSharingReport(Resource):
    """
    Admin-only account-sharing report. Returns aggregates keyed by HMAC'd email — never raw
    emails — so it is safe even though the ecommerce app is internet-facing.

    GET /plugin/sharing_report?min_instances=2&window_hours=24
        header: X-Admin-Key: <ECOMMERCE_ADMIN_KEY>
    """

    def __init__(self, access_logic: AccessLogic = None):
        self._access_logic = access_logic or AccessLogic()

    def get(self):
        admin_key = environ.get(_ENV_ADMIN_KEY)
        if not admin_key or request.headers.get('X-Admin-Key') != admin_key:
            return {'message': 'unauthorized'}, 401

        try:
            min_instances = int(request.args.get('min_instances', 2))
            window_hours = int(request.args.get('window_hours', 24))
        except (TypeError, ValueError):
            return {'message': 'min_instances and window_hours must be integers'}, 400

        return {
            'tracking_enabled': self._access_logic.enabled,
            'accounts': self._access_logic.get_sharing_report(min_instances, window_hours),
        }, 200
