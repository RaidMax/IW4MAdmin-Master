"""
Dev utility: generate an ECDSA P-256 keypair for plugin entitlement signing.

    python -m ecommerce.encryption.generate_signing_keypair

Prints:
  - the PKCS#8 PEM PRIVATE key  -> set as ECOMMERCE_SIGNING_KEY on the store (keep secret!)
  - the SubjectPublicKeyInfo base64 PUBLIC key -> embed in the plugin's EntitlementService
    (PublicKeySpkiB64).

Run once to mint the production keypair; never commit the private key.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def main():
    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode('utf-8')
    spki = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    print('=== PRIVATE KEY (ECOMMERCE_SIGNING_KEY — keep secret) ===')
    print(pem)
    print('=== PUBLIC KEY (embed in plugin EntitlementService.PublicKeySpkiB64) ===')
    print(base64.b64encode(spki).decode('utf-8'))


if __name__ == '__main__':
    main()
