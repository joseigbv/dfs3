"""
Module: client.py
Description: MQTT client utilities for dfs3 event broadcasting.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
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

import json
import paho.mqtt.client as mqtt

from config.settings import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC
from utils.logger import LOG, ERR, DBG
from core import context


def publish_event(block_id: str, event: dict):
    """
    Publishes the given block_id to the DFS3 MQTT topic to notify other nodes.

    Args:
        block_id: The IOTA block ID as a string.

    Returns:
        None
    """

    try:
        # Enviar solo el block_id por MQTT
        msg = {
            "block_id": block_id,
            "event_type": event["event_type"],
            "timestamp": event["timestamp"],
            "node_id": event["node_id"]
        }

        # Publicación con persistencia
        client = mqtt.Client()
        #cliente.tls_set()
        client.connect(MQTT_BROKER, int(MQTT_PORT))
        client.publish(MQTT_TOPIC, json.dumps(msg), qos=1)
        client.disconnect()

        LOG(f"Block ID sent over MQTT: {block_id}")
        DBG(f"MQTT event published: {json.dumps(msg)}")

    except Exception as e:
        ERR(f"Failed to send block ID over MQTT: {e}")


def register_client():
    """
    Register the current node as a persistent MQTT client and subscribe to the network topic.

    This function creates an MQTT client with a persistent session (clean_session=False)
    using the node ID as the client identifier. It connects to the MQTT broker, subscribes
    to the designated topic with QoS level 1 to ensure reliable message delivery, and
    briefly enters the loop to initialize the connection before disconnecting.

    Note:
        This function is typically used during node registration or network bootstrapping
        to announce presence or ensure subscription status.

    Raises:
        KeyError: If 'node_id' is missing from the configuration context.
        socket.error: If the MQTT broker is unreachable.
        mqtt.MQTTException: For general client-related errors.
    """

    # Crear cliente, client_id y clean_session=False para que sea persistente
    client = mqtt.Client(
        client_id=context.config['node_id'], 
        clean_session=False
    )

    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_TOPIC, qos=1)
    client.loop()
    client.disconnect()

