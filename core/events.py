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
import sqlite3

from core import context
from typing import List
from contextlib import closing
from utils.logger import LOG, WRN, ERR, DBG
from utils.system import get_uptime_seconds, get_total_disk_space, get_ip
from utils.time import iso_now
from utils.crypto import sign_event
from config.settings import DATA_DIR, API_PORT, DB_FILE
from iota.client import publish_event as publish_event_to_iota
from mqtt.client import publish_event as publish_event_to_mqtt
from models.base import EventEntry
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

 
def save_event(block_id: str, event: BaseEvent):
    """
    Saves a minimal reference of an event into the local SQLite database.
    """
    event_type = event.event_type
    timestamp = int(event.timestamp.timestamp())
    node_id = event.node_id

    try:
        with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
            cursor.execute("""
                INSERT INTO events (block_id, event_type, timestamp, node_id)
                VALUES (?, ?, ?, ?)
            """, (block_id, event_type, timestamp, node_id))

            conn.commit()

        LOG(f"Event {event_type} saved in DB with block_id {block_id} from node {node_id}.")

    except Exception as e:
        ERR(f"Failed to save event {event_type} in DB: {e}")


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
        "ip": get_ip(),
        "port": int(context.config.get("port", API_PORT)),
        "tags": context.config.get("tags", []),
        "version": 1
    }

    if not (base_event := build_base_event(EV_NODE_REGISTERED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := NodeRegisteredEvent(**base_event.dict())):
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
        "ip": get_ip(),
        "port": int(context.config.get("port", API_PORT)),
        "uptime": get_uptime_seconds(),
        "total_space": get_total_disk_space()
    }

    if not (base_event := build_base_event(EV_NODE_STATUS, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := NodeStatusEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_user_registered_event(payload: dict) -> str | None:
    """
    Builds a user_created event from the given user registration data.
    """
    if not (base_event := build_base_event(EV_USER_REGISTERED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := UserRegisteredEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_user_joined_node_event(payload: dict) -> str | None:
    """
    Builds a user_joined_node event from the given login verification data.
    """
    if not (base_event := build_base_event(EV_USER_JOINED_NODE, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := UserJoinedNodeEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_created_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_created' using the given UploadFileMetadata payload.
    """
    if not (base_event := build_base_event(EV_FILE_CREATED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := FileCreatedEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_shared_event(payload: dict) -> str | None: 
    """
    Constructs a BaseEvent of type 'file_shared' using the given ShareFileRequest payload.
    """
    if not (base_event := build_base_event(EV_FILE_SHARED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := FileSharedEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_accessed_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_accessed' using the given file request payload.
    """
    if not (base_event := build_base_event(EV_FILE_ACCESSED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := FileAccessedEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_deleted_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_deleted' using the given file request payload.
    """
    if not (base_event := build_base_event(EV_FILE_DELETED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := FileDeletedEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_renamed_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_renamed' using the given file request payload.
    """
    if not (base_event := build_base_event(EV_FILE_RENAMED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := FileRenamedEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def send_file_replicated_event(payload: dict) -> str | None:
    """
    Constructs a BaseEvent of type 'file_replicated' using the given file request payload.
    """
    if not (base_event := build_base_event(EV_FILE_REPLICATED, payload)):
        ERR("Error creating base event.")
        return None

    if not (event := FileReplicatedEvent(**base_event.dict())):
        ERR("Error creating event.")
        return None

    # si todo va bien, publicamos evento 
    return publish_event(event)


def list_events() -> List[EventEntry]:
    """
    Returns the list of users from database
    """     
    with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
        cursor.execute("""
            SELECT timestamp, block_id, event_type, node_id 
            FROM events
            WHERE event_type <> "node_status"
            UNION
            SELECT timestamp, block_id, event_type, node_id 
            FROM events e1 JOIN (
                SELECT MAX(rowid) AS max_rowid 
                FROM events 
                WHERE event_type = 'node_status' 
                GROUP BY node_id) e2 
            WHERE e1.rowid = e2.max_rowid
            ORDER BY timestamp
        """)
    
        return [
            EventEntry(timestamp=timestamp, block_id=block_id, event_type=event_type, node_id=node_id)
            for timestamp, block_id, event_type, node_id in cursor.fetchall()
        ]


def get(block_id: str) -> EventEntry | None:
    """
    Retrieves a user by user_id from cache or database.
    """
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cursor:
            cursor.execute("""
                SELECT timestamp, block_id, event_type, node_id
                FROM events
                WHERE block_id = ?
            """, (block_id,))

            return (
                EventEntry(timestamp=r['timestamp'], block_id=r['block_id'], event_type=r['event_type'], node_id=r['node_id'])
                if (r := cursor.fetchone()) else None
            )

