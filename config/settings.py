"""
Module: settings.py
Description: Centralized configuration for dfs3 system. Loads defaults and overrides from environment variables or .env file.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-04-30
"""
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

from os import path, getenv
from dotenv import load_dotenv
from core.constants import Verbosity

# Carga automáticamente el archivo .env
load_dotenv()  


# ---
# Editar a partir de aqui
# ---

# Nivel global de verbosidad
VERBOSITY_LEVEL = getenv("DFS3_VERBOSITY_LEVEL", Verbosity.DEBUG) 

# MQTT Configuration
MQTT_BROKER = getenv("DFS3_MQTT_BROKER", "mqtt.dfs3.net")
MQTT_PORT = int(getenv("DFS3_MQTT_PORT", 1883))
MQTT_TOPIC = getenv("DFS3_MQTT_TOPIC", "dfs3/events")

# Directorio donde iran todos los datos
DATA_DIR = getenv("DFS3_DATA_DIR", "data")

# Fichero de configuracion node.json
CONFIG_PATH = getenv("DFS3_CONFIG_PATH", path.join(DATA_DIR, "node.json"))

# Database
DB_FILE = getenv("DFS3_DB_FILE", path.join(DATA_DIR, "dfs3.db"))

# Certificado TLS
SSL_KEYFILE = getenv("DFS3_SSL_KEYFILE", path.join(DATA_DIR, "privkey.pem"))
SSL_CERTFILE = getenv("DFS3_SSL_CERTFILE", path.join(DATA_DIR, "fullchain.pem"))

# Storage dir
STORAGE_DIR = getenv("DFS3_STORAGE_DIR", path.join(DATA_DIR, ".storage"))

# Meta dir
META_DIR = getenv("DFS3_META_DIR", path.join(DATA_DIR, ".meta"))

# Users dir
USERS_DIR = getenv("DFS3_USERS_DIR", path.join(DATA_DIR, ".users"))

# Verbosity (LOW=1, MEDIUM=2, HIGH=3)
LOG_VERBOSITY = getenv("DFS3_LOG_VERBOSITY", Verbosity.HIGH)

# URL de acceso al nodo IOTA usado para las pruebas
IOTA_NODE_URL = getenv("DFS3_IOTA_NODE_URL", "https://iota.dfs3.net/api/core/v2/blocks")

# URL de acceso al nodo "seed", usado para sincronizar estado de nodos nuevos
SEED_NODE_URL = getenv("DFS3_SEED_NODE_URL", "https://node.dfs3.net/api/v1/events")

# Puerto en el que se ejecuta el servicio
API_PORT = int(getenv("DFS3_API_PORT", 443))

# Cada cuanto actualizamos el estado del nodo
UPDATE_STATUS_INTERVAL = int(getenv("DFS3_UPDATE_STATUS_INTERVAL", 300))

