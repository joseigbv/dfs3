"""
Module: listener.py
Description: MQTT listener for dfs3. Subscribes to the events topic and handles incoming block_id notifications.
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
import paho.mqtt.client as mqtt

from utils.logger import LOG, WRN, ERR, DBG
from core.constants import VALID_EVENT_TYPES, SHA256_HEX_PATTERN, Verbosity
from config.settings import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC
from core.event_handler import process_event
from core import context
from iota.client import fetch_event


def on_connect(client, userdata, flags, rc):
    """
    Callback triggered when the MQTT client connects to the broker.

    Subscribes to the configured topic if the connection was successful.

    Args:
        client: The MQTT client instance.
        userdata: Private user data (not used).
        flags: Response flags sent by the broker.
        rc: The connection result code.
    """

    if rc == 0:
        LOG(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")

        # Suscribirse al topic, qos=1/2 para hacerlo persistente
        client.subscribe(MQTT_TOPIC, qos=1)
        LOG(f"Subscribed to topic: {MQTT_TOPIC}")

    else:
        ERR(f"Failed to connect to MQTT broker, return code {rc}")


def validate_event(data: dict) -> bool:
    """
    Validates the MQTT message structure and contents.

    Ensures required fields exist, types are correct, and that 'block_id'
    and 'source_node_id' match SHA-256 hex format.

    Args:
        data: Parsed JSON dictionary from MQTT message.

    Returns:
        True if valid, False otherwise.
    """
 
    # Estos campos son obligatorios
    required_fields = {"block_id", "event_type", "timestamp", "node_id"}

    # TODO: aniadir validacion de timestamp
    if not isinstance(data, dict):
        return False
    if not required_fields.issubset(data.keys()):
        return False
    if data["event_type"] not in VALID_EVENT_TYPES:
        return False
    if not SHA256_HEX_PATTERN.match(data["block_id"]):
        return False
    if not SHA256_HEX_PATTERN.match("0x" + data["node_id"]):
        return False

    return True


def fetch_and_process_event(block_id: str):
    """
    Simulates retrieval of an event from IOTA using the block_id, then processes it.

    Args:
        block_id: The identifier of the block in the Tangle containing the event.
    """

    LOG(f"Fetching event from IOTA with block_id: {block_id}", level=Verbosity.HIGH)

    # Nos metemos ya con el evento real de IOTA
    event = fetch_event(block_id)
    process_event(event, block_id)


def on_message(client, userdata, msg):
    """
    Callback triggered when a message is received from the broker.

    Logs the received block_id contained in the MQTT message payload.

    Args:
        client: The MQTT client instance.
        userdata: Private user data (not used).
        msg: The received MQTT message.
    """

    try:
        payload = msg.payload.decode('utf-8')
        LOG(f"Received MQTT message on topic '{msg.topic}': {payload}", level=Verbosity.HIGH)

        event = json.loads(payload)
        if not validate_event(event):
            WRN("Invalid MQTT event format")
            return

        block_id = event["block_id"]
        fetch_and_process_event(block_id)

    except Exception as e:
        ERR(f"Error processing MQTT message: {str(e)}")


def start_listener():
    """
    Initializes the MQTT client and starts listening for messages on the configured topic.

    This function blocks if using loop_forever(), or starts a background thread if using loop_start().
    """

    # Conecta a la cola mqtt
    client = mqtt.Client(
        client_id=context.config["node_id"], 
        clean_session=False
    )

    # Usa TLS confiando en las CA del sistema operativo
    # client.tls_set()

    # Asignar callback
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        #client.loop_forever()

    except Exception as e:
        ERR(f"MQTT connection error: {str(e)}")

