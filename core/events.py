"""
Module: events.py
Description: Tools for building and publishing dfs3 system events, including signature generation and MQTT/IOTA dispatch.
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
import base64
import datetime
import platform

from config.settings import DATA_DIR, PORT
from core import context
from core.constants import SW_VERSION, PROTOCOL
from utils.logger import LOG, WRN, ERR, DBG
from utils.system import get_uptime_seconds, get_total_disk_space, get_local_ip
from utils.time import iso_now
from utils.crypto import sign_event
from iota.client import publish_event as publish_event_to_iota
from mqtt.client import publish_event as publish_event_to_mqtt


def publish_event(event: dict):
    """
    Publishes an event to IOTA and notifies other nodes via MQTT with the resulting block_id.

    Args:
        event: The full event dictionary to be published.

    Returns:
        None
    """

    try:
        LOG(f"Publishing event to IOTA: {event['event_type']}")
        block_id = publish_event_to_iota(event)
        LOG(f"Event published to IOTA with block_id: {block_id}")

        # Send block_id via MQTT as control channel
        publish_event_to_mqtt(block_id, event)

    except Exception as e:
        ERR(f"Failed to publish event: {e}")

    
def build_node_registered_event() -> dict:
    """
    Constructs a node_registered event from the given node config and signs it.

    Returns:
        A dictionary representing the signed node_registered event.
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
        "port": int(context.config.get("port", PORT)),
        "tags": context.config.get("tags", []),
    }

    event = {
        "event_type": "node_registered",
        "timestamp": iso_now(),
        "node_id": context.config["node_id"],
        "protocol": PROTOCOL,
        "payload": payload
    }

    # Firmamos
    event["signature"] = sign_event(event, context.private_key)
    DBG(f"Event: {event}")

    return event


def build_node_status_event() -> dict:
    """
    Constructs a node_status event including dynamic status info and a digital signature.

    Returns:
        The full event dictionary ready for publishing.
    """

    payload = {
        "ip": get_local_ip(),
        "port": int(context.config.get("port", PORT)),
        "uptime": get_uptime_seconds(),
        "total_space": get_total_disk_space()
    }

    event = {
        "event_type": "node_status",
        "timestamp": iso_now(),
        "node_id": context.config["node_id"],
        "protocol": PROTOCOL,
        "payload": payload,
    }

    # Firmamos
    event["signature"] = sign_event(event, context.private_key)
    DBG(f"Event: {event}")

    return event

