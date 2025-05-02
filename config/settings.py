"""
Module: settings.py
Description: Centralized configuration for dfs3 system. Loads defaults and overrides from environment variables or .env file.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-04-30
"""

# =============================================================
# MIT License
# Copyright (c) 2025 José Ignacio
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

import os
from dotenv import load_dotenv
from core.constants import Verbosity

# Carga automáticamente el archivo .env
load_dotenv()  


# ---
# Editar a partir de aqui
# ---

# Nivel global de verbosidad
VERBOSITY_LEVEL = os.environ.get("DFS3_VERBOSITY_LEVEL", Verbosity.DEBUG) 

# Fichero de configuración
CONFIG_PATH = os.environ.get("DFS_CONFIG_PATH", "config/node.json")

# MQTT Configuration
MQTT_BROKER = os.environ.get("DFS3_MQTT_BROKER", "mqtt.dfs3.net")
MQTT_PORT = int(os.environ.get("DFS3_MQTT_PORT", 1883))
MQTT_TOPIC = os.environ.get("DFS3_MQTT_TOPIC", "dfs3/events")

# Directorio donde iran todos los datos
DATA_DIR = os.environ.get("DFS3_DATA_DIR", "data")

# Database
DB_FILE = os.path.join(DATA_DIR, "dfs3.db")

# Verbosity (LOW=1, MEDIUM=2, HIGH=3)
LOG_VERBOSITY = Verbosity.HIGH

# URL de acceso al nodo IOTA usado para las pruebas
IOTA_NODE_URL = os.getenv("DFS3_IOTA_NODE_URL", "https://iota.dfs3.net/api/core/v2/blocks")

# Puerto en el que se ejecuta el servicio
PORT = os.getenv("DFS3_PORT", 1234)

