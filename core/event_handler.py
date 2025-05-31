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
from utils.logger import LOG, WRN, ERR, DBG
from core import context
from core.constants import VALID_EVENT_TYPES, SHA256_HEX_PATTERN, EV_NODE_REGISTERED
from core.events import save_event
from core.nodes import (
    save as save_node, 
    update as update_node, 
    get_public_key as get_public_key_node
)
from core.users import (
    register as register_user, 
    update as update_user
)
from core.files import (
    create as create_file, 
    share as share_file,
    rename as rename_file,
    delete as delete_file,
    replicate as replicate_file, 
)
from models.events import (
    BaseEvent, 
    NodeRegisteredEvent,
    NodeStatusEvent,
    UserRegisteredEvent,
    UserJoinedNodeEvent,
    FileCreatedEvent, 
    FileSharedEvent,
    FileAccessedEvent,
    FileRenamedEvent,
    FileDeletedEvent,
    FileReplicatedEvent
)


def verify_signature(event: BaseEvent) -> bool:
    """
    Verifies the digital signature of a signed dfs3 event.
    """
    # Solo en el caso de alta de nodo, se saca la clave publica del evento
    if event.event_type == EV_NODE_REGISTERED:
        public_key_bytes = b64decode(event.payload["public_key"])

    else:
        # Deberiamos tener el node_id en db
        if not (public_key_b64 := get_public_key_node(event.node_id)):
            ERR(f"Public key not found for node {event.node_id}")
            return False

        public_key_bytes = b64decode(public_key_b64)

    # Reconstruimos el contenido firmado (sin signature) para validar firma
    # BUG: Object of type datetime is not JSON serial...
    event_dict = json.loads(event.json(exclude={"signature"})) 
    content = json.dumps(event_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = b64decode(event.signature)

    try:
        # Verificamos signature o error
        verify_key = VerifyKey(public_key_bytes, encoder=RawEncoder)
        verify_key.verify(content, signature)

    except BadSignatureError as e:
        ERR(f"Invalid signature: {e}")
        return False

    return True


def handle_node_registered(event: BaseEvent, block_id: str):
    """
    Handles a node_status event.
    """
    # TODO Temporal para pruebas
    event.payload['version'] = 1

    save_node(NodeRegisteredEvent(**event.dict()))
    LOG(f"Node registered from {block_id}")


def handle_node_status(event: BaseEvent, block_id: str):
    """
    Handles a node_status event.
    """
    update_node(NodeStatusEvent(**event.dict()))
    LOG(f"Node updated from {block_id}")


def handle_user_registered(event: BaseEvent, block_id: str):
    """
    Handles a user_created event by registering the user and storing the event reference.
    """
    register_user(UserRegisteredEvent(**event.dict()))
    LOG(f"User registered from {block_id}")


def handle_user_joined_node(event: BaseEvent, block_id: str):
    """
    Handles a user_joined_node event by recording the event reference for audit purposes.
    """
    update_user(UserJoinedNodeEvent(**event.dict()))
    LOG(f"User updated from {block_id}")


def handle_file_created(event: BaseEvent, block_id: str):
    """
    Handles a file_created event by storing the event reference and preparing for future replication.
    """
    # TODO temporal para pruebas, reconvertir eventos
    if (owner := event.payload.pop('owner', None)):
       event.payload["user_id"] = owner
    event.payload.pop('creation_date', None)
    event.payload.pop('replica_nodes', None)
    event.payload.pop('version', None)

    create_file(FileCreatedEvent(**event.dict()))
    LOG(f"File created from {block_id}")


def handle_file_shared(event: BaseEvent, block_id: str):
    """
    Handles a file_shared event by storing the event reference and sharing the file.
    """
    share_file(FileSharedEvent(**event.dict()))
    LOG(f"File shared from {block_id}")


def handle_file_accessed(event: BaseEvent, block_id: str):
    """
    Handles a file_accessed event by storing the event reference.
    """
    # TODO: De momento, no hacemos mas, ya esta registrado el evento
    LOG(f"File accessed from {block_id}")


def handle_file_renamed(event: BaseEvent, block_id: str):
    """
    Handles a file_renamed event by storing the event reference and renaming the entry.
    """
    rename_file(FileRenamedEvent(**event.dict()))
    LOG(f"File renamed from {block_id}")


def handle_file_deleted(event: BaseEvent, block_id: str):
    """
    Handles a file_deleted event by storing the event reference and deleting the entry.
    """
    delete_file(FileDeletedEvent(**event.dict()))
    LOG(f"File deleted from {block_id}")


def handle_file_replicated(event: BaseEvent, block_id: str):
    """
    Handles a file_replicated event by storing the event reference and updating the entry.
    """
    replicate_file(FileReplicatedEvent(**event.dict()))
    LOG(f"File replicated from {block_id}")


def handle_generic(event: BaseEvent, block_id: str):
    """
    Handles generic / not defined events.
    """
    WRN(f"Handler for generic event: {event}")


# Declaración de handlers para manejo de eventos
EVENT_HANDLERS = {
    "node_registered": handle_node_registered,
    "node_status": handle_node_status,
    "user_registered": handle_user_registered,
    "user_joined_node": handle_user_joined_node,
    "file_created": handle_file_created,
    "file_shared": handle_file_shared,
    "file_accessed": handle_file_accessed,
    "file_renamed": handle_file_renamed,
    "file_deleted": handle_file_deleted,
    "file_replicated": handle_file_replicated
}


def process_event(event: BaseEvent, block_id: str):
    """
    Processes a IOTA event by validating and dispatching it to the appropriate handler.
    """
    DBG(f"IOTA event {block_id}: {event}")
    if not verify_signature(event):
        WRN(f"Invalid IOTA event: {block_id}")
        return

    # Ejecutamos el manejador para ese tipo de evento
    if (handler := EVENT_HANDLERS.get(event.event_type)):
        handler(event, block_id)

    else:
        WRN(f"No handler defined for event type: {event.event_type}")

    LOG(f"Saving event to DB: {block_id}")
    save_event(block_id, event)

