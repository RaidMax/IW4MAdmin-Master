import logging
from datetime import datetime, timedelta, timezone

from flask import request
from flask_restful import Resource

from ecommerce.encryption.signing_helper import canonical_payload, sign
from ecommerce.integrations.logic.customer_logic import CustomerLogic

logger = logging.getLogger(__name__)

# Short TTL keeps a leaked token useful only briefly; the plugin re-checks well before expiry.
ENTITLEMENT_TTL_HOURS = 12


class PluginEntitlement(Resource):
    """
    Issues a short-lived, signed entitlement token proving the calling instance has an
    active subscription for the requested plugin. The plugin verifies the signature with
    an embedded public key and fails closed when enforcement is enabled.

    GET /plugin/entitlement?subscription_id=<email>&instance_id=<guid>&plugin_id=<id>&nonce=<n>
    -> 200 {"data": "<signed json string>", "signature": "<base64 DER>"}
    -> 403 when the subscription does not cover the plugin (client fails closed)
    """

    def __init__(self, customer_logic: CustomerLogic = None):
        self._customer_logic = customer_logic or CustomerLogic()

    def get(self):
        subscription_id = request.args.get('subscription_id')
        instance_id = request.args.get('instance_id')
        plugin_id = request.args.get('plugin_id')
        nonce = request.args.get('nonce')

        if not all([subscription_id, instance_id, plugin_id, nonce]):
            return {'message': 'subscription_id, instance_id, plugin_id and nonce are required'}, 400

        try:
            entitled = self._customer_logic.get_entitled_plugin_ids(subscription_id)
        except Exception as ex:
            logger.error('could not resolve entitlements', exc_info=ex)
            return {'message': 'could not resolve entitlement'}, 502

        if plugin_id not in entitled:
            return {'message': 'not entitled', 'entitled': False}, 403

        issued = datetime.now(timezone.utc)
        expiry = issued + timedelta(hours=ENTITLEMENT_TTL_HOURS)
        payload = {
            'plugin_id': plugin_id,
            'instance_id': instance_id,
            'nonce': nonce,
            'issued_at': issued.isoformat(),
            'expiry': expiry.isoformat(),
            'entitled': True,
        }

        # Sign the exact serialized string and return it verbatim, so the plugin verifies
        # against bytes it never has to reconstruct (no cross-language canonicalization risk).
        data = canonical_payload(payload)
        return {'data': data, 'signature': sign(data)}, 200
