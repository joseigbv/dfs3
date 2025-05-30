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
import requests

from contextlib import closing
from base64 import b64encode
from nacl.signing import SigningKey
from nacl.encoding import RawEncoder
from nacl.secret import SecretBox
from nacl.utils import random as nacl_random
from nacl.pwhash import argon2id
from typing import Optional, List
from core import context
from core.constants import SOFTWARE_VERSION
from utils.crypto import decrypt_private_key
from utils.logger import LOG, WRN, ERR, DBG, ABR
from utils.db import row_to_dict
from config.settings import CONFIG_PATH, DB_FILE, API_PORT, SEED_NODE_URL
from models.base import NodeEntry, EventEntry
from models.events import NodeRegisteredEvent, NodeStatusEvent
from cachetools import LRUCache, cached


# Para cachear claves publicas y reducir lectura a db
_public_key_cache: LRUCache[str, Optional[str]] = LRUCache(maxsize=100)
_node_cache: LRUCache[str, Optional[dict]] = LRUCache(maxsize=10)

def invalidate_node_cache(node_id: str) -> None:
    _node_cache.pop(node_id, None)
    _public_key_cache.pop(node_id, None)


def derive_key_from_passphrase(passphrase: str) -> tuple[bytes, bytes]:
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
        "software_version": SOFTWARE_VERSION,
        "node_id": node_id,
        "port": API_PORT,
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
    """
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


def save(event: NodeRegisteredEvent):
    """
    Saves or updates a node in the local database based on a node_registered event.
    """
    node_id = event.node_id
    payload = event.payload

    alias = payload.alias
    hostname = payload.hostname
    public_key = payload.public_key
    platform = payload.platform
    software_version = payload.software_version
    uptime = payload.uptime
    total_space = payload.total_space
    ip = str(payload.ip)
    port = payload.port
    tags = ",".join(payload.tags or [])
    version = payload.version

    tstamp = int(event.timestamp.timestamp())
    creation_date = tstamp
    last_seen = tstamp

    # Si en cache, invalidamos
    invalidate_node_cache(node_id)

    try:
        with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
            cursor.execute("""
                INSERT INTO nodes (
                    node_id, alias, hostname, public_key,
                    platform, software_version, uptime, total_space,
                    ip, port, tags, creation_date, version, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    alias=excluded.alias,
                    hostname=excluded.hostname,
                    public_key=excluded.public_key,
                    platform=excluded.platform,
                    software_version=excluded.software_version,
                    uptime=excluded.uptime,
                    total_space=excluded.total_space,
                    ip=excluded.ip,
                    port=excluded.port,
                    tags=excluded.tags,
                    creation_date=excluded.creation_date,
                    version=excluded.version,
                    last_seen=excluded.last_seen
            """, (
                node_id, alias, hostname, public_key,
                platform, software_version, uptime, total_space,
                ip, port, tags, creation_date, version, last_seen
            ))

            conn.commit()

        # invalidamos cache (deberia estar en None)
        invalidate_node_cache(node_id)

        LOG(f"Node '{alias}' ({node_id}) saved to database")

    except Exception as e:
        ERR(f"Failed to save node to database: {e}")


def update(event: NodeStatusEvent):
    """
    Updates dynamic fields of an existing node in the database based on a node_status event.
    """
    node_id = event.node_id
    payload = event.payload

    ip = str(payload.ip)
    port = payload.port
    uptime = payload.uptime
    total_space = payload.total_space

    last_seen = int(event.timestamp.timestamp())

    # Si en cache, invalidamos
    invalidate_node_cache(node_id)

    try:
        with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
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

    except Exception as e:
        ERR(f"Failed to update node from status event: {e}")


@cached(_node_cache, key=lambda node_id: node_id)
def get(node_id: str) -> dict | None:
    """
    Retrieves a node from the database by node_id.
    """
    # Consultamos en db si no esta en cache
    with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
        cursor.execute("""
            SELECT * 
            FROM nodes 
            WHERE node_id = ?
        """, (node_id,))

        # TODO convertir en una clase
        if (row := cursor.fetchone()):
            return row_to_dict(cursor, row)

    # Si llegamos, mal
    return None


@cached(_public_key_cache, key=lambda node_id: node_id)
def get_public_key(node_id: str) -> str | None:
    """
    Retrieves the base64-encoded public key of a node from the database by node_id.
    """
    return node["public_key"] if (node := get(node_id)) else None


def should_clone_from(source_node_id: str, size: int) -> bool:
    """
    Buscamos los tres nodos que tengan espacio suficiente, lleven activos mas de 
    10 minutos y esten levantados desde hace mas de 1 día
    """ 
    # TODO para pruebas, cualquier nodo vale
    return context.config["node_id"] != source_node_id

    with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
        cursor.execute("""
            SELECT node_id
            FROM nodes
            WHERE uptime >= 86400
              AND last_seen >= datetime('now', '-10 minutes')
              AND total_space > ?
              AND node_id != ?
            ORDER BY total_space DESC, node_id ASC
            LIMIT 3;
        """, (size, source_node_id))

        # Generamos la lista de candidatos, TODO parametrizar
        candidates = [r[0] for r in cursor.fetchall()]

    # somos candidatos ?
    return context.config["node_id"] in candidates


def list_nodes() -> List[NodeEntry]:
    """
    Returns the list of nodes from database
    """
    with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor: 
        cursor.execute("""
            SELECT node_id, alias, public_key
            FROM nodes;
        """)

        return [
            NodeEntry(node_id=node_id, alias=alias, public_key=public_key) 
            for node_id, alias, public_key in cursor.fetchall()
        ]


def sync_node_status():
    # para evitar dependencias circulares
    from mqtt.listener import fetch_and_process_event
    try:
        # Petición para obtener la lista de eventos
        response = requests.get(SEED_NODE_URL)
        response.raise_for_status()

        # Generamos la lista de eventos
        events = [EventEntry(**e) for e in response.json()]
        DBG(f"Retrieved {len(events)} events")

        for event in events:
            DBG(f"Processing event {event.block_id} {event.event_type}")
            fetch_and_process_event(event.block_id)

    except Exception as e:
        ABR(f"Error syncing events: {e}")

