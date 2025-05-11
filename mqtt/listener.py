"""
Module: mqtt/listener.py
Description: MQTT listener for dfs3. Subscribes to the events topic and handles 
incoming block_id notifications.
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

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from utils.logger import LOG, WRN, ERR, DBG, ABR
from core.constants import Verbosity
from config.settings import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC
from core import context
from core.event_handler import process_event
from iota.client import fetch_event
from models.events import MqttEventNotification


def on_connect(client, userdata, flags, rc):
    """
    Callback triggered when the MQTT client connects to the broker and
    subscribes to the configured topic if the connection was successful.
    """
    LOG(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    if rc == 0:
        # Suscribirse al topic, qos=1/2 para hacerlo persistente
        LOG(f"Subscribed to topic: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC, qos=1)

    else:
        ABR(f"Failed to connect to MQTT broker, return code {rc}")


def fetch_and_process_event(block_id: str):
    """
    Retrieval of an event from IOTA using the block_id, then processes it.
    """
    LOG(f"Fetching event from IOTA with block_id: {block_id}", level=Verbosity.HIGH)
    event = fetch_event(block_id)
    process_event(event, block_id)


def on_message(client, userdata, msg):
    """
    Callback triggered when a message is received from the broker.
    """
    try:
        # Paho le llama 'payload' al contenido mensaje mqtt
        payload = msg.payload.decode('utf-8')
        LOG(f"Received MQTT message on topic '{msg.topic}': {payload}", level=Verbosity.HIGH)

        # Validamos formato del evento
        try:
            event = MqttEventNotification.parse_raw(payload)
            # TODO: añadir validacion de timestamp y filtrar caracteres de entrada

        except ValidationError as e:
            WRN("Invalid MQTT event format: {str(e)}")
            return

        # Iniciamos descarga y proesamiento de evento completo
        fetch_and_process_event(event.block_id)

    except Exception as e:
        ERR(f"Error processing MQTT message {event.block_id}: {str(e)}")


def start():
    """
    Initializes the MQTT client and starts listening for messages on the configured topic.
    """
    client = mqtt.Client(client_id=context.config["node_id"], clean_session=False)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

    except Exception as e:
        ABR(f"MQTT connection error: {str(e)}")

