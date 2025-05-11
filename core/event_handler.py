"""
Module: core/event_handler.py
Description: Validates and dispatches dfs3 events to appropriate handlers by type.
Author: José Ignacio
License: MIT
Created: 2025-05-01
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

import json
import sqlite3

from base64 import b64decode
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from nacl.encoding import RawEncoder
from config.settings import DATA_DIR
from utils.logger import LOG, WRN, ERR, DBG
from utils.time import iso_to_epoch
from core.constants import VALID_EVENT_TYPES, SHA256_HEX_PATTERN
from core.nodes import save_node, update_node, get_node_public_key
from core.users import register as register_user
from core.files import create as create_file 
from core import context


def save_event_to_db(block_id: str, event: dict):
    """
    Saves a minimal reference of an event into the local SQLite database.
    """
    try:
        event_type = event["event_type"]
        timestamp = iso_to_epoch(event["timestamp"])
        node_id = event["node_id"]

        conn = sqlite3.connect(f"{DATA_DIR}/dfs3.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO events (block_id, event_type, timestamp, node_id)
            VALUES (?, ?, ?, ?)
        """, (block_id, event_type, timestamp, node_id))

        conn.commit()
        conn.close()
    
        LOG(f"Event {event_type} saved in DB with block_id {block_id} from node {node_id}.")
        
    except Exception as e:
        ERR(f"Failed to save event {event_type} in DB: {e}")


def verify_signature(event: dict) -> bool:
    """
    Verifies the digital signature of a signed dfs3 event.
    """
    # Solo en el caso de alta de nodo, se saca la clave publica del evento
    if event['event_type'] == 'node_registered':
        public_key_bytes = b64decode(event["payload"]["public_key"])
    else:
        # Deberiamos tener el node_id en db
        public_key_bytes = b64decode(get_node_public_key(event['node_id']))

    # Primero nos quedamos con la firma
    signature = b64decode(event["signature"])

    # Eliminamos para reconstruir el contenido firmado
    event_copy = event.copy()
    del event_copy["signature"]

    # Verificamos signature o error
    content = json.dumps(event_copy, separators=(",", ":"), sort_keys=True).encode("utf-8")
    verify_key = VerifyKey(public_key_bytes, encoder=RawEncoder)
    verify_key.verify(content, signature)

    return True


def validate_event(event: dict) -> bool:
    """
    Validates the structure and content of a IOTA event.
    """
    # Estos campos son obligatorios
    required_fields = {"event_type", "timestamp", "node_id", "payload", "signature"}

    # TODO: aniadir validacion de timestamp y filtrar caracteres de entrada
    if not isinstance(event, dict):
        return False
    if not required_fields.issubset(event.keys()):
        return False
    if event["event_type"] not in VALID_EVENT_TYPES:
        return False
    if not SHA256_HEX_PATTERN.match("0x" + event["node_id"]):
        return False

    # La firma es valida?
    try:
        verify_signature(event)
        return True

    except (KeyError, ValueError, BadSignatureError) as e:
        WRN(f"Invalid signature: {e}")
        return False


def handle_node_registered(event: dict, block_id: str):
    """
    Handles a node_status event.
    """
    # Almacenamos en db
    save_node(event)

    LOG(f"Node registered from {block_id}")


def handle_node_status(event: dict, block_id: str):
    """
    Handles a node_status event.
    """
    # Actualizamos en db
    update_node(event)

    LOG(f"Node updated from {block_id}")


def handle_user_registered(event: dict, block_id: str):
    """
    Handles a user_created event by registering the user and storing the event reference.
    """
    # TODO: Validar 
    register_user(event)

    LOG(f"User registered from {block_id}")


def handle_user_joined_node(event: dict, block_id: str):
    """
    Handles a user_joined_node event by recording the event reference for audit purposes.
    """
    # De momento no es necesario hacer nada, ya registra evento en DB e IOTA
    pass


def handle_file_created(event: dict, block_id: str):
    """
    Handles a file_created event by storing the event reference and preparing for future replication.
    """
    # TODO: Validar 
    create_file(event)

    LOG(f"File created from {block_id}")


def handle_generic(event: dict, block_id: str):
    """
    Handles generic / not defined events.
    """
    WRN(f"Handler for generic event: {event}")


# Placeholder: aquí irán más handlers como handle_file_created(), handle_user_updated(), etc.
EVENT_HANDLERS = {
    "node_registered": handle_node_registered,
    "node_status": handle_node_status,
    "user_registered": handle_user_registered,
    "user_joined_node": handle_user_joined_node,
    "file_created": handle_file_created,
    # ...
}


def process_event(event: dict, block_id: str):
    """
    Processes a IOTA event by validating and dispatching it to the appropriate handler.
    """
    DBG(f"IOTA event {block_id}: {event}")

    # Primero, es correcto el formato del mensaje IOTA?
    if not validate_event(event):
        WRN(f"Invalid IOTA event: {block_id}")
        return

    # Ahora ya procedemos a ejecutar el manejador para ese tipo 
    event_type = event["event_type"]
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        handler(event, block_id)

    else:
        WRN(f"No handler defined for event type: {event_type}")

    LOG(f"Saving event to DB: {block_id}")
    save_event_to_db(block_id, event)

