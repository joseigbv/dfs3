"""
Module: event_handler.py
Description: Validates and dispatches dfs3 events to appropriate handlers by type.
Author: José Ignacio
License: MIT
Created: 2025-05-01
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

import base64
import json

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from nacl.encoding import RawEncoder

from utils.logger import LOG, WRN, ERR, DBG
from core.constants import VALID_EVENT_TYPES, SHA256_HEX_PATTERN
from core.nodes import save_node, update_node
from core import context


def verify_signature(event: dict) -> bool:
    """
    Verifies the digital signature of a signed dfs3 event.

    Args:
        event: The complete event dictionary including 'signature'.

    Returns:
        True if the signature is valid, False otherwise.
    """

    # TODO: temporal, la public_key no deberia salir del evento
    #public_key_bytes = base64.b64decode(event["payload"]["public_key"])
    public_key_bytes = base64.b64decode(context.config["keys"]["public_key"])

    # Primero nos quedamos con la firma
    signature = base64.b64decode(event["signature"])

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

    Args:
        event: Event data as a dictionary (from IOTA). 

    Returns:
        True if the event is structurally / semantically valid and well signed, False otherwise.
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

    Args:
        event: The validated event dictionary.
    """

    # Almacenamos en db
    save_node(event)

    LOG(f"Node registered from {block_id}")


def handle_node_status(event: dict, block_id: str):
    """
    Handles a node_status event.

    Args:
        event: The validated event dictionary.
    """

    # Actualizamos en db
    update_node(event)

    LOG(f"Node updated from {block_id}")


def handle_generic(event: dict, block_id: str):
    LOG(f"[HANDLER] generic event: {event}")


# Placeholder: aquí irán más handlers como handle_file_created(), handle_user_updated(), etc.
EVENT_HANDLERS = {
    "node_registered": handle_node_registered,
    "node_status": handle_node_status,
    # "file_created": handle_file_created,
    # "user_updated": handle_user_updated,
    # ...
}


def process_event(event: dict, block_id: str):
    """
    Processes a IOTA event by validating and dispatching it to the appropriate handler.

    Args:
        event: Event dictionary to process.
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

