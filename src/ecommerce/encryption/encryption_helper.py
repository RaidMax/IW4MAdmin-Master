import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def encrypt_data(data: bytes, seed: str, salt: str) -> bytes:
    """
    :param data: data to encrypt
    :param seed: pass phrase
    :param salt: salt phrase
    :return: bytes cipher + tag + nonce
    """
    seed_bytes = seed.encode('utf-8')
    salt = salt.encode('utf-8')
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA512(),
        length=32,
        salt=salt,
        iterations=10000,
        backend=default_backend()
    )
    key = kdf.derive(seed_bytes)
    nonce = os.urandom(12)

    aes = AESGCM(key)
    cipher_data_bytes = aes.encrypt(
        nonce=nonce,
        data=data,
        associated_data=None
    )
    return cipher_data_bytes + nonce
