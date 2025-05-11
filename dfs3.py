#!/usr/bin/env python3
"""
Module: dfs3.py
Description: Main entry point for the dfs3 distributed file system
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

import threading
import asyncio

from utils.logger import LOG, WRN, ERR, DBG
from config.settings import UPDATE_STATUS_INTERVAL
from core import context
from core.db_init import create_db
from core.nodes import init_or_load_node
from core.events import publish_event, build_node_registered_event, build_node_status_event
from mqtt.listener import start as start_mqtt_listener
from mqtt.client import register as register_mqtt_client
from api.server import start_api


def show_banner():
    """
    Display the dfs3 system banner in the console.

    This function prints a formatted text banner or logo representing the dfs3
    system. It is typically called at startup to provide a visual cue that the
    node or application has launched correctly.

    This is a purely cosmetic/logging function and does not return anything.

    """

    print(r"""
      _  __     _____ 
   __| |/ _|___|___ / 
  / _` | |_/ __| |_ \ 
 | (_| |  _\__ \___) |
  \__,_|_| |___/____/ 
                             
  dfs3 0.1 - Distributed File Storage System for IoT with Blockchain
  Author: José Ignacio Bravo <nacho.bravo@gmail.com>

  """)


async def main():
    """
    Main entry point for the dfs3 system.

    Initializes the database (if needed), starts the MQTT listener, and keeps the 
    program running.

    """

    show_banner()

    LOG("Starting dfs3 system...")
    create_db()

    LOG("Loading node config...")
    config, private_key, is_new = init_or_load_node()

    # Contexto para compartir con el resto de modulos de forma segura
    context.config = config
    context.private_key = private_key

    # Si es la primera vez, registramos el nodo en la red
    if is_new:
        # workaround para que el nodo vea su propio mensaje 
        register_mqtt_client()

        LOG("Node created successfully. Publishing registration event...")
        event = build_node_registered_event()
        block_id = publish_event(event)

    LOG("Starting MQTT listener...")
    start_mqtt_listener()

    LOG("Starting API REST listener...")
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    LOG(f"Node ID: {config['node_id']} loaded and ready")
    try:
        while True:
            await asyncio.sleep(UPDATE_STATUS_INTERVAL)

            # TODO: En un hilo diferente para no bloquear asyncio?
            LOG("Update node status...")
            event = build_node_status_event()
            block_id = publish_event(event)

    except KeyboardInterrupt:
        LOG("Shutting down MQTT listener...")

    LOG("Bye!")


if __name__ == '__main__':
    asyncio.run(main())

