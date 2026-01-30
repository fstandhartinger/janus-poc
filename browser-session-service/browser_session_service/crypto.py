"""Encryption/decryption utilities using AES-256-GCM."""

import base64
import hashlib
import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# AES-256-GCM uses 12-byte (96-bit) nonces for optimal performance
NONCE_SIZE = 12


def derive_user_key(server_secret: bytes, user_id: str) -> bytes:
    """
    Derive a per-user encryption key using HKDF.

    This ensures each user's sessions are encrypted with a unique key derived
    from the server secret and their user ID.

    Args:
        server_secret: 32-byte master secret
        user_id: User identifier from Chutes IDP JWT

    Returns:
        32-byte derived key for AES-256
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,  # Use default salt
        info=f"browser-session:{user_id}".encode(),
    )
    return hkdf.derive(server_secret)


def encrypt_storage_state(
    storage_state_json: str,
    server_secret: bytes,
    user_id: str,
) -> Tuple[bytes, bytes]:
    """
    Encrypt storage state JSON using AES-256-GCM.

    Args:
        storage_state_json: JSON string of the storage state
        server_secret: 32-byte master secret
        user_id: User identifier for key derivation

    Returns:
        Tuple of (ciphertext, nonce/iv)
    """
    key = derive_user_key(server_secret, user_id)
    aesgcm = AESGCM(key)

    # Generate random nonce
    nonce = os.urandom(NONCE_SIZE)

    # Encrypt the storage state
    plaintext = storage_state_json.encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return ciphertext, nonce


def decrypt_storage_state(
    ciphertext: bytes,
    nonce: bytes,
    server_secret: bytes,
    user_id: str,
) -> str:
    """
    Decrypt storage state using AES-256-GCM.

    Args:
        ciphertext: Encrypted storage state
        nonce: Initialization vector used during encryption
        server_secret: 32-byte master secret
        user_id: User identifier for key derivation

    Returns:
        Decrypted JSON string

    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails (wrong key or tampered data)
    """
    key = derive_user_key(server_secret, user_id)
    aesgcm = AESGCM(key)

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def decode_secret(secret_b64: str) -> bytes:
    """
    Decode a base64-encoded secret.

    Args:
        secret_b64: Base64-encoded 32-byte secret

    Returns:
        32-byte secret

    Raises:
        ValueError: If secret is not exactly 32 bytes after decoding
    """
    try:
        secret = base64.b64decode(secret_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 encoding for secret: {e}")

    if len(secret) != 32:
        raise ValueError(f"Secret must be exactly 32 bytes, got {len(secret)}")

    return secret


def generate_secret() -> str:
    """
    Generate a new random 32-byte secret encoded as base64.

    This is a utility for generating new secrets - not used at runtime.

    Returns:
        Base64-encoded 32-byte secret
    """
    return base64.b64encode(os.urandom(32)).decode("ascii")
