"""
Module: nodes.py
Description: Manages creation and loading of node identity and secure config.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-04-30
"""

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

import os
import hashlib
import datetime
import json
import getpass
import sqlite3

from base64 import b64encode
from nacl.signing import SigningKey
from nacl.encoding import RawEncoder
from nacl.secret import SecretBox
from nacl.utils import random as nacl_random
from nacl.pwhash import argon2id

from core.constants import SW_VERSION
from utils.crypto import decrypt_private_key
from utils.logger import LOG, WRN, ERR, DBG
from utils.time import iso_to_epoch
from config.settings import CONFIG_PATH, DATA_DIR, DB_FILE, PORT


def derive_key_from_passphrase(passphrase: str) -> bytes:
    """
    Derives a 32-byte seed from the user's passphrase and salt using Argon2id.
    """
    
    salt = nacl_random(16)
    key = argon2id.kdf(
        SecretBox.KEY_SIZE,
        passphrase.encode(),
        salt,
        opslimit=argon2id.OPSLIMIT_MODERATE,
        memlimit=argon2id.MEMLIMIT_MODERATE
    )

    return key, salt


def generate_node_identity(passphrase: str, alias: str, tags: list[str]) -> tuple[dict, bytes]:
    """
    Generates a new Ed25519 keypair and returns all data needed for config.json.
    """

    # seed used to derive private key deterministically
    seed, salt_private_key = derive_key_from_passphrase(passphrase)
    signing_key = SigningKey(seed)
    public_key_bytes = signing_key.verify_key.encode(encoder=RawEncoder)
    node_id = hashlib.sha256(public_key_bytes).hexdigest()

    # salt used to encrypt private key for validation and secure storage
    secret_key, salt_encryption = derive_key_from_passphrase(passphrase)
    box = SecretBox(secret_key)
    encrypted_private_key = box.encrypt(signing_key.encode(), encoder=RawEncoder)

    config = {
        "hostname": os.uname().nodename,
        "alias": alias,
        "creation_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": SW_VERSION,
        "node_id": node_id,
        "port": PORT,
        "tags": tags,
        "keys": {
            "salt_private_key": b64encode(salt_private_key).decode(),
            "salt_encryption": b64encode(salt_encryption).decode(),
            "public_key": b64encode(public_key_bytes).decode(),
            "private_key_encrypted": b64encode(encrypted_private_key).decode()
        }
    }

    return config, signing_key.encode()


def init_or_load_node(config_path: str = CONFIG_PATH) -> tuple[dict, bytes, bool]:
    """
    Loads existing node configuration or creates one if it doesn't exist.

    Returns:
        The configuration dictionary with node_id and keys, private key and whether it's new or not.
    """

    # Si ya existe el fichero, lo cargamos
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Ahora necesitamos desbloquear la clave privada
        passphrase = getpass.getpass("Enter passphrase to decrypt private key: ")
        try:
            private_key = decrypt_private_key(config, passphrase)

        except Exception as e:
            ERR(f"Failed to decrypt private key: {e}")

        return config, private_key, False


    # Validación previa de passphrase antes de crear claves
    while True:
        pw1 = getpass.getpass("Enter new passphrase to protect your private key: ")
        pw2 = getpass.getpass("Repeat passphrase: ")
        if pw1 == pw2:
            passphrase = pw1
            break

        else:
            print("Passphrases do not match. Please try again.")

    # Si el nodo no esta registrado, genera un fichero de configuracion
    alias = input("Enter a friendly alias for this node: ").strip()
    tags_input = input("Enter tags for this node (comma-separated): ").strip()
    tags = tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    config, private_key = generate_node_identity(passphrase, alias, tags)

    # Guardamos a disco
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return config, private_key, True


def save_node(event: dict):
    """
    Saves or updates a node in the local database based on a node_registered event.

    Args:
        event: The full event dictionary validated from IOTA.
    """

    node_id = event["node_id"]
    payload = event["payload"]

    alias = payload["alias"]
    hostname = payload.get("hostname", "")
    version = payload.get("version", 1)
    public_key = payload["public_key"]
    platform = payload.get("platform", "")
    software_version = payload.get("software_version", "")
    uptime = payload["uptime"]
    total_space = payload["total_space"]
    ip = payload["ip"]
    port = payload["port"]
    tags = ",".join(payload.get("tags", []))

    creation_date = iso_to_epoch(event["timestamp"])
    last_seen = iso_to_epoch(event["timestamp"])

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO nodes (
                node_id, alias, hostname, version, public_key,
                platform, software_version, uptime, total_space,
                ip, port, tags, creation_date, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                alias=excluded.alias,
                hostname=excluded.hostname,
                version=excluded.version,
                public_key=excluded.public_key,
                platform=excluded.platform,
                software_version=excluded.software_version,
                uptime=excluded.uptime,
                total_space=excluded.total_space,
                ip=excluded.ip,
                port=excluded.port,
                tags=excluded.tags,
                creation_date=excluded.creation_date,
                last_seen=excluded.last_seen
        """, (
            node_id, alias, hostname, version, public_key,
            platform, software_version, uptime, total_space,
            ip, port, tags, creation_date, last_seen
        ))

        conn.commit()
        conn.close()

        LOG(f"Node '{alias}' ({node_id}) saved to database")

    except Exception as e:
        ERR(f"Failed to save node to database: {e}")


def update_node(event: dict):
    """
    Updates dynamic fields of an existing node in the database based on a node_status event.

    Args:
        event: The full event dictionary validated from IOTA.
    """

    node_id = event["node_id"]
    payload = event["payload"]

    ip = payload["ip"]
    port = payload["port"]
    uptime = payload["uptime"]
    total_space = payload["total_space"]

    last_seen = iso_to_epoch(event["timestamp"])

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE nodes SET
                ip = ?,
                port = ?,
                uptime = ?,
                total_space = ?,
                last_seen = ?
            WHERE node_id = ?
        """, (
            ip, port, uptime, total_space, last_seen, node_id
        ))

        if cursor.rowcount == 0:
            WRN(f"Node {node_id} not found in DB for update.")

        else:
            LOG(f"Node {node_id} updated with node_status info.")

        conn.commit()
        conn.close()

    except Exception as e:
        ERR(f"Failed to update node from status event: {e}")


def get_node_public_key(node_id: str) -> str:
    """
    Retrieves the base64-encoded public key of a node from the database by node_id.

    Args:
        node_id: The unique ID of the node.

    Returns:
        The public key as a base64 string.
    """

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT public_key FROM nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()

        return row[0]

    except Exception as e:
        ERR(f"Failed to retrieve public key for node {node_id}: {e}")

