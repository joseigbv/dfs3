"""
Module: crypto.py
Description: Provides cryptographic utilities for key decryption and verification.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-04-30
"""

# =============================================================
# MIT License
# Copyright (c) 2025 José Ignacio Bravo <nacho.bravo@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Change history:
#   2025-04-30 - José Ignacio Bravo - Initial creation
# =============================================================

import json

from base64 import b64encode, b64decode
from nacl.secret import SecretBox
from nacl.pwhash import argon2id
from nacl.encoding import RawEncoder
from nacl.exceptions import CryptoError, BadSignatureError
from nacl.signing import SigningKey, VerifyKey


def decrypt_private_key(config: dict, passphrase: str) -> bytes:
    """
    Decrypts the encrypted private key using the passphrase and salt_encryption.

    Args:
        config: The loaded config.json dictionary containing encryption metadata.
        passphrase: The passphrase provided by the user.

    Returns:
        The decrypted private key bytes.

    Raises:
        CryptoError: If decryption fails (e.g. wrong passphrase).
    """

    salt_b64 = config["keys"]["salt_encryption"]
    encrypted_b64 = config["keys"]["private_key_encrypted"]

    salt = b64decode(salt_b64)
    encrypted = b64decode(encrypted_b64)

    key = argon2id.kdf(
        SecretBox.KEY_SIZE,
        passphrase.encode(),
        salt,
        opslimit=argon2id.OPSLIMIT_MODERATE,
        memlimit=argon2id.MEMLIMIT_MODERATE
    )

    box = SecretBox(key)

    return box.decrypt(encrypted, encoder=RawEncoder)


def sign_event(event: dict, private_key: bytes) -> str:
    """
    Signs the entire event dictionary (excluding the signature field) using the Ed25519 private key.

    Args:
        event: The event dictionary to sign. Must not yet include the "signature" field.
        private_key: The raw private key in bytes used to sign the event.

    Returns:
        The signature as a base64-encoded string.

    Raises:
        Exception if the signing process fails.
    """

    # Firmar todo el evento (sin signature)
    signing_key = SigningKey(private_key)
    event_bytes = json.dumps(event, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = signing_key.sign(event_bytes, encoder=RawEncoder).signature

    return b64encode(signature).decode()


def verify_signature(public_key: str, text: str, signature: str) -> bool:
    try:
        verify_key = VerifyKey(b64decode(public_key))
        verify_key.verify(text.encode(), b64decode(signature))

    except (BadSignatureError, Exception):
        return False

    return True

