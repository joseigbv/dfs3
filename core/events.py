"""
Module: events.py
Description: Tools for building and publishing dfs3 system events, including signature generation and MQTT/IOTA dispatch.
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

import platform

from config.settings import DATA_DIR, API_PORT
from core import context
from utils.logger import LOG, WRN, ERR, DBG
from utils.system import get_uptime_seconds, get_total_disk_space, get_local_ip
from utils.time import iso_now
from utils.crypto import sign_event
from iota.client import publish_event as publish_event_to_iota
from mqtt.client import publish_event as publish_event_to_mqtt
from core.constants import (
    PROTOCOL, 
    EV_NODE_REGISTERED, 
    EV_NODE_STATUS, 
    EV_USER_REGISTERED, 
    EV_USER_JOINED_NODE, 
    EV_FILE_CREATED, 
    EV_FILE_SHARED,
    EV_FILE_ACCESSED,
    EV_FILE_DELETED,
    EV_FILE_RENAMED,
    EV_FILE_REPLICATED
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
    FileDeletedEvent,
    FileRenamedEvent,
    FileReplicatedEvent,
)


def publish_event(event: BaseEvent) -> str | None:
    """
    Publishes an event to IOTA and notifies other nodes via MQTT with the resulting block_id.
    """
    try:
        LOG(f"Publishing event to IOTA: {event.event_type}")
        block_id = publish_event_to_iota(event)

        LOG(f"Publishing event to MQTT: {block_id}")
        publish_event_to_mqtt(block_id, event)

    except Exception as e:
        ERR(f"Failed to publish event: {e}")
        return None

    return block_id;

 
def build_base_event(event_type: str, payload: dict) -> BaseEvent | None:
    """
    Constructs an event with the given type and payload, adding metadata fields and signs it.
    """
    # Vamos a verificar que private_key existe
    if not context.config:
        ERR("Config not found in context.")
        return None

    event_dict = {
        "event_type": event_type,
        "timestamp": iso_now(),
        "node_id": context.config["node_id"],
        "protocol": PROTOCOL,
        "payload": payload
    }

    # Vamos a verificar que private_key existe
    if not context.private_key:
        ERR("Private key not found in context.")
        return None

    # Firma solo los datos, no el contenedor
    event_dict["signature"] = sign_event(event_dict, context.private_key)  
    DBG(f"Event: {event_dict}")

    return BaseEvent(**event_dict)


def send_node_registered_event() -> str | None:
    """
    Constructs a node_registered event from the given node config and signs it.
    """
    # Vamos a verificar que private_key existe
    if not context.config:
        ERR("Config not found in context.")
        return None

    payload = {
        "alias": context.config.get("alias", "unnamed-node"),
        "hostname": context.config["hostname"],
        "public_key": context.config["keys"]["public_key"], 
        "platform": platform.platform(),
        "software_version": context.config["software_version"],
        "uptime": get_uptime_seconds(),
        "total_space": get_total_disk_space(DATA_DIR),
        "ip": get_local_ip(),
        "port": int(context.config.get("port", API_PORT)),
        "tags": context.config.get("tags", []),
        "version": 1
    }

    base_event = build_base_event(EV_NODE_REGISTERED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = NodeRegisteredEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_node_status_event() -> str | None:
    """
    Constructs a node_status event including dynamic status info and a digital signature.
    """
    # Vamos a verificar que private_key existe
    if not context.config:
        ERR("Config not found in context.")
        return None

    payload = {
        "ip": get_local_ip(),
        "port": int(context.config.get("port", API_PORT)),
        "uptime": get_uptime_seconds(),
        "total_space": get_total_disk_space()
    }

    base_event = build_base_event(EV_NODE_STATUS, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = NodeStatusEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_user_registered_event(payload: dict) -> str | None:
    """
    Builds a user_created event from the given user registration data.
    """
    base_event = build_base_event(EV_USER_REGISTERED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = UserRegisteredEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_user_joined_node_event(payload: dict) -> str | None:
    """
    Builds a user_joined_node event from the given login verification data.
    """
    base_event = build_base_event(EV_USER_JOINED_NODE, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = UserJoinedNodeEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_created_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_created' using the given UploadFileMetadata payload.
    """
    base_event = build_base_event(EV_FILE_CREATED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = FileCreatedEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_shared_event(payload: dict) -> str | None: 
    """
    Constructs a BaseEvent of type 'file_shared' using the given ShareFileRequest payload.
    """
    base_event = build_base_event(EV_FILE_SHARED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = FileSharedEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_accessed_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_accessed' using the given file request payload.
    """
    base_event = build_base_event(EV_FILE_ACCESSED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = FileAccessedEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_deleted_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_deleted' using the given file request payload.
    """
    base_event = build_base_event(EV_FILE_DELETED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = FileDeletedEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_renamed_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_renamed' using the given file request payload.
    """
    base_event = build_base_event(EV_FILE_RENAMED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = FileRenamedEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_replicated_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_replicated' using the given file request payload.
    """
    base_event = build_base_event(EV_FILE_REPLICATED, payload)
    if not base_event:
        ERR("Error creating base event.")
        return None

    event = FileReplicatedEvent(**base_event.dict())
    if not event:
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)

