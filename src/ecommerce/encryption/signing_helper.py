"""
ECDSA (P-256 / SECP256R1, SHA-256) signing for plugin entitlements.

The plugin embeds the matching PUBLIC key and verifies signatures locally. The PRIVATE
key lives only here and must be supplied in production via the ECOMMERCE_SIGNING_KEY env
var (PKCS#8 PEM). The baked-in key below is a DEV key for local testing only.

ECDSA was chosen over Ed25519 because it is supported natively by both `cryptography`
(here) and the .NET BCL (`System.Security.Cryptography.ECDsa`) on the plugin side, with
no extra dependency. Signatures are emitted in DER (RFC 3279) form; the .NET verifier must
use DSASignatureFormat.Rfc3279DerSequence to match.
"""

import base64
import json
import logging
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)

_ENV_PRIVATE_KEY = 'ECOMMERCE_SIGNING_KEY'

# DEV-ONLY private key. DO NOT use in production — set ECOMMERCE_SIGNING_KEY instead.
# The matching public key is embedded in the plugin's EntitlementService.
_DEV_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg2eFtjzxzl+IuD0zV
7Zt6q3RMzwwhnq8l+PNO6CXg3QKhRANCAARNKZj9cyoiOc+uNYbCz1MlbtYZNEjU
SzBVkLceqWp52I/XjCMSVKJEYWriAavkF3mbAxJFOLUoQCVBUEpPyta1
-----END PRIVATE KEY-----"""


def canonical_payload(payload: dict) -> str:
    """Deterministic JSON string. This exact string is what gets signed and what the
    plugin verifies the signature against (the plugin never re-serializes it), so the
    formatting here is not load-bearing across languages — it only needs to be stable."""
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


def _load_private_key():
    pem = os.environ.get(_ENV_PRIVATE_KEY)
    if not pem:
        logger.warning('%s not set — using INSECURE dev signing key', _ENV_PRIVATE_KEY)
        pem = _DEV_PRIVATE_KEY_PEM
    return serialization.load_pem_private_key(pem.encode('utf-8'), password=None)


def sign(data: str) -> str:
    """Signs the given string and returns a base64 DER signature."""
    key = _load_private_key()
    signature = key.sign(data.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode('utf-8')
