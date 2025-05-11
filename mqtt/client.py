"""
Module: mqtt/client.py
Description: MQTT client utilities for dfs3 event broadcasting.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
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
import paho.mqtt.client as mqtt

from config.settings import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC
from utils.logger import LOG, WRN, ERR, DBG, ABR
from core import context
from models.events import MqttEventNotification


def publish_event(block_id: str, event: dict):
    """
    Publishes the given block_id to the MQTT topic to notify other nodes.
    """
    try:
        # Enviar solo el block_id e  info mínima por MQTT
        msg = MqttEventNotification(
            block_id=block_id,
            event_type=event["event_type"],
            timestamp=event["timestamp"],
            node_id=event["node_id"]
        )

        # Publicación con persistencia
        client = mqtt.Client()
        client.connect(MQTT_BROKER, int(MQTT_PORT))
        client.publish(MQTT_TOPIC, msg.json(), qos=1)
        client.disconnect()

        LOG(f"Block ID sent over MQTT: {block_id}")
        DBG(f"MQTT event published: {msg}")

    except Exception as e:
        # TODO: Revisar flujo de errores
        ABR(f"Failed to send block ID over MQTT: {e}")


def register():
    """
    Register the current node as a persistent MQTT client and subscribe to the network topic.
    """
    client = mqtt.Client(client_id=context.config['node_id'], clean_session=False)
    client.connect(MQTT_BROKER, int(MQTT_PORT))
    client.subscribe(MQTT_TOPIC, qos=1)
    client.loop() # hack
    client.disconnect()

