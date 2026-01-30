"""Tests for encryption/decryption utilities."""

import base64
import os

import pytest

from browser_session_service.crypto import (
    NONCE_SIZE,
    decode_secret,
    decrypt_storage_state,
    derive_user_key,
    encrypt_storage_state,
    generate_secret,
)


class TestDeriveUserKey:
    """Tests for key derivation."""

    def test_derive_user_key_returns_32_bytes(self):
        """Key derivation should return a 32-byte key."""
        server_secret = os.urandom(32)
        key = derive_user_key(server_secret, "user-123")
        assert len(key) == 32

    def test_different_users_get_different_keys(self):
        """Different users should get different encryption keys."""
        server_secret = os.urandom(32)
        key1 = derive_user_key(server_secret, "user-1")
        key2 = derive_user_key(server_secret, "user-2")
        assert key1 != key2

    def test_same_user_gets_same_key(self):
        """Same user should always get the same key."""
        server_secret = os.urandom(32)
        key1 = derive_user_key(server_secret, "user-123")
        key2 = derive_user_key(server_secret, "user-123")
        assert key1 == key2

    def test_different_secrets_produce_different_keys(self):
        """Different server secrets should produce different keys."""
        secret1 = os.urandom(32)
        secret2 = os.urandom(32)
        key1 = derive_user_key(secret1, "user-123")
        key2 = derive_user_key(secret2, "user-123")
        assert key1 != key2


class TestEncryptDecrypt:
    """Tests for encryption and decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encryption followed by decryption should return original data."""
        server_secret = os.urandom(32)
        user_id = "test-user"
        original = '{"cookies": [], "origins": []}'

        ciphertext, nonce = encrypt_storage_state(original, server_secret, user_id)
        decrypted = decrypt_storage_state(ciphertext, nonce, server_secret, user_id)

        assert decrypted == original

    def test_encrypt_produces_different_output_each_time(self):
        """Each encryption should produce unique ciphertext (due to random nonce)."""
        server_secret = os.urandom(32)
        user_id = "test-user"
        plaintext = '{"cookies": [{"name": "test"}]}'

        ct1, nonce1 = encrypt_storage_state(plaintext, server_secret, user_id)
        ct2, nonce2 = encrypt_storage_state(plaintext, server_secret, user_id)

        # Different nonces mean different ciphertext
        assert nonce1 != nonce2
        assert ct1 != ct2

    def test_nonce_has_correct_size(self):
        """Nonce should be 12 bytes (96 bits) for AES-GCM."""
        server_secret = os.urandom(32)
        _, nonce = encrypt_storage_state('{"test": 1}', server_secret, "user")
        assert len(nonce) == NONCE_SIZE == 12

    def test_wrong_user_cannot_decrypt(self):
        """Decryption with wrong user ID should fail."""
        server_secret = os.urandom(32)
        original = '{"secret": "data"}'

        ciphertext, nonce = encrypt_storage_state(original, server_secret, "user-1")

        with pytest.raises(Exception):  # InvalidTag from cryptography
            decrypt_storage_state(ciphertext, nonce, server_secret, "user-2")

    def test_wrong_secret_cannot_decrypt(self):
        """Decryption with wrong server secret should fail."""
        secret1 = os.urandom(32)
        secret2 = os.urandom(32)
        original = '{"secret": "data"}'

        ciphertext, nonce = encrypt_storage_state(original, secret1, "user")

        with pytest.raises(Exception):  # InvalidTag
            decrypt_storage_state(ciphertext, nonce, secret2, "user")

    def test_tampered_ciphertext_fails(self):
        """Tampered ciphertext should fail authentication."""
        server_secret = os.urandom(32)
        user_id = "test-user"

        ciphertext, nonce = encrypt_storage_state('{"data": 1}', server_secret, user_id)

        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF
        tampered = bytes(tampered)

        with pytest.raises(Exception):  # InvalidTag
            decrypt_storage_state(tampered, nonce, server_secret, user_id)

    def test_unicode_content(self):
        """Encryption should handle Unicode content."""
        server_secret = os.urandom(32)
        user_id = "test-user"
        original = '{"message": "Hello, 世界! \u2764\ufe0f"}'

        ciphertext, nonce = encrypt_storage_state(original, server_secret, user_id)
        decrypted = decrypt_storage_state(ciphertext, nonce, server_secret, user_id)

        assert decrypted == original

    def test_large_storage_state(self):
        """Encryption should handle large storage states."""
        server_secret = os.urandom(32)
        user_id = "test-user"
        # Create a ~100KB storage state
        large_data = '{"cookies": [' + ','.join(['{"name": "c%d"}' % i for i in range(1000)]) + ']}'

        ciphertext, nonce = encrypt_storage_state(large_data, server_secret, user_id)
        decrypted = decrypt_storage_state(ciphertext, nonce, server_secret, user_id)

        assert decrypted == large_data


class TestDecodeSecret:
    """Tests for secret decoding."""

    def test_valid_secret_decoding(self):
        """Valid base64 secret should decode to 32 bytes."""
        # Generate a proper 32-byte secret
        original = os.urandom(32)
        encoded = base64.b64encode(original).decode()

        decoded = decode_secret(encoded)
        assert decoded == original
        assert len(decoded) == 32

    def test_invalid_base64_raises(self):
        """Invalid base64 should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid base64"):
            decode_secret("not-valid-base64!!!")

    def test_wrong_length_raises(self):
        """Secret that's not 32 bytes should raise ValueError."""
        short_secret = base64.b64encode(os.urandom(16)).decode()
        with pytest.raises(ValueError, match="must be exactly 32 bytes"):
            decode_secret(short_secret)

        long_secret = base64.b64encode(os.urandom(64)).decode()
        with pytest.raises(ValueError, match="must be exactly 32 bytes"):
            decode_secret(long_secret)


class TestGenerateSecret:
    """Tests for secret generation."""

    def test_generate_secret_format(self):
        """Generated secret should be valid base64 encoding 32 bytes."""
        secret = generate_secret()

        # Should be valid base64
        decoded = base64.b64decode(secret)
        assert len(decoded) == 32

    def test_generate_secret_uniqueness(self):
        """Each generated secret should be unique."""
        secrets = [generate_secret() for _ in range(10)]
        assert len(set(secrets)) == 10
