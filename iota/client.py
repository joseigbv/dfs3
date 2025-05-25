"""
Module: iota/client.py
Description: Handles interaction with IOTA node to publish events using tagged data payloads.
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

import requests
import json

from config.settings import IOTA_NODE_URL
from utils.logger import LOG, WRN, ERR, DBG, ABR
from models.events import BaseEvent


def publish_event(event: BaseEvent, tag: str = "dfs3") -> str:
    """
    Publishes a JSON event to the IOTA Tangle using tagged data payload.
    """
    block = {
        "protocolVersion": 2,
        "payload": {
            "type": 5,  # TaggedData
            "tag": "0x" + tag.encode("utf-8").hex(),
            "data": "0x" + event.json().encode("utf-8").hex()
        }
    }

    # Enviamos mensaje como peticion http
    response = requests.post(IOTA_NODE_URL, json=block)
    if response.status_code in [201, 202]:
        block_id = response.json()["blockId"]
        LOG(f"Event published to IOTA with block_id: {block_id}")
        return block_id

    else:
        raise RuntimeError(f"Failed to publish event: {response.status_code} - {response.text}")


def fetch_event(block_id: str) -> BaseEvent | None:
    """
    Retrieves and parses a JSON event from IOTA using its block ID.
    """
    # Buscamos el bloque en IOTA a traves de su URL
    response = requests.get(f"{IOTA_NODE_URL}/{block_id}")
    if response.status_code != 200:
        raise RuntimeError(f"Error fetching block: {response.status_code} - {response.text}")

    # Extraemos payload (IOTA lo llama asi) que es nuestro evento
    payload = response.json().get("payload", {})
    if payload.get("type") != 5:
        ERR("Block does not contain TaggedDataPayload.")
        return None

    try:
        data_hex = payload.get("data", "")
        real_bytes = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
        json_text = real_bytes.decode("utf-8")
  
        # Validamos y convertimos a objeto
        event = BaseEvent.parse_raw(json_text)

    except Exception as e:
        ERR(f"Failed to decode event data: {e}")
        return None

    return event 

