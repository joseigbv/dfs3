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

import json
import base64
import datetime
import platform

from config.settings import DATA_DIR, API_PORT
from core import context
from core.constants import SW_VERSION, PROTOCOL, EV_NODE_REGISTERED, EV_NODE_STATUS, EV_USER_REGISTERED, EV_USER_JOINED_NODE, EV_FILE_CREATED
from utils.logger import LOG, WRN, ERR, DBG
from utils.system import get_uptime_seconds, get_total_disk_space, get_local_ip
from utils.time import iso_now
from utils.crypto import sign_event
from iota.client import publish_event as publish_event_to_iota
from mqtt.client import publish_event as publish_event_to_mqtt


def publish_event(event: dict) -> str | None:
    """
    Publishes an event to IOTA and notifies other nodes via MQTT with the resulting block_id.
    """
    try:
        LOG(f"Publishing event to IOTA: {event['event_type']}")
        block_id = publish_event_to_iota(event)

        LOG(f"Publishing event to MQTT: {block_id}")
        publish_event_to_mqtt(block_id, event)

    except Exception as e:
        ERR(f"Failed to publish event: {e}")

    return block_id;

 
def build_event(event_type: str, payload: dict) -> dict:
    """
    Constructs an event with the given type and payload, adding metadata fields and signs it.
    """
    event = {
        "event_type": event_type,
        "timestamp": iso_now(),
        "node_id": context.config["node_id"],
        "protocol": PROTOCOL,
        "payload": payload
    }

    # Firma solo los datos, no el contenedor
    event["signature"] = sign_event(event, context.private_key)  
    DBG(f"Event: {event}")

    return event


def build_node_registered_event() -> dict:
    """
    Constructs a node_registered event from the given node config and signs it.
    """
    payload = {
        "alias": context.config.get("alias", "unnamed-node"),
        "hostname": context.config["hostname"],
        "version": context.config["version"],
        "public_key": context.config["keys"]["public_key"], 
        "platform": platform.platform(),
        "software_version": SW_VERSION,
        "uptime": get_uptime_seconds(),
        "total_space": get_total_disk_space(DATA_DIR),
        "ip": get_local_ip(),
        "port": int(context.config.get("port", API_PORT)),
        "tags": context.config.get("tags", []),
    }

    return build_event(EV_NODE_REGISTERED, payload)


def build_node_status_event() -> dict:
    """
    Constructs a node_status event including dynamic status info and a digital signature.
    """
    payload = {
        "ip": get_local_ip(),
        "port": int(context.config.get("port", API_PORT)),
        "uptime": get_uptime_seconds(),
        "total_space": get_total_disk_space()
    }

    return build_event(EV_NODE_STATUS, payload)


def build_user_registered_event(payload: dict) -> dict:
    """
    Builds a user_created event from the given user registration data.
    """
    # TODO: Revisar tratamiento de payload
    return build_event(EV_USER_REGISTERED, payload)


def build_user_joined_node_event(payload: dict) -> dict:
    """
    Builds a user_joined_node event from the given login verification data.
    """
    # TODO: Revisar tratamiento de payload
    return build_event(EV_USER_JOINED_NODE, payload)


def build_file_created_event(payload: dict) -> dict:
    # TODO: verificar payload, asumimos que viene bien de la api (pydantic)
    payload["creation_date"] = iso_now()
    payload["version"] = 1
    payload["replica_nodes"] = [context.config["node_id"]]

    return build_event(EV_FILE_CREATED, payload)

