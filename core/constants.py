"""
Module: core/constants.py
Description: Central definitions for constants and global patterns used throughout dfs3
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

import re
from enum import IntEnum


# Utilizada para definir el nivel de logging
class Verbosity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    DEBUG = 4


# Lista global de tipos de eventos válidos en dfs3
EV_USER_REGISTERED = "user_registered"
EV_USER_JOINED_NODE = "user_joined_node"
EV_NODE_REGISTERED = "node_registered"
EV_NODE_STATUS = "node_status"
EV_FILE_CREATED = "file_created"
EV_FILE_DELETED = "file_deleted"
EV_FILE_SHARED = "file_shared"
EV_FILE_COPIED = "file_copied"
EV_FILE_REPLICATED = "file_replicated"
EV_FILE_RENAMED = "file_renamed"
EV_FILE_ACCESSED = "file_accessed"
EV_FILE_DELETED = "file_deleted"
EV_FILE_RENAMED = "file_renamed"
EV_FILE_REPLICATED = "file_replicated"

VALID_EVENT_TYPES = {
    EV_USER_REGISTERED,
    EV_USER_JOINED_NODE,
    EV_NODE_REGISTERED, 
    EV_NODE_STATUS,
    EV_FILE_CREATED,
    EV_FILE_DELETED,
    EV_FILE_SHARED,
    EV_FILE_COPIED,
    EV_FILE_REPLICATED,
    EV_FILE_RENAMED,
    EV_FILE_ACCESSED,
    EV_FILE_DELETED,
    EV_FILE_RENAMED,
    EV_FILE_REPLICATED
}

# Version de software y de protocolo
SOFTWARE_VERSION = "dfs3-node/0.3.1" 
PROTOCOL = "dfs3/1.0"

# Otras expresiones regulares para validacion
RE_BLOCK_ID: str = r"^0x[a-f0-9]{64}$"
RE_USER_ID: str = r"^[a-f0-9]{64}$"
RE_ALIAS: str = r"^[a-z0-9_-]{3,20}$"
RE_FILE_ID: str = RE_USER_ID
RE_NODE_ID: str = RE_USER_ID
#RE_FILENAME: str = r"^[\w\-. ]{1,100}$" # mas restrictiva 
RE_FILENAME: str = r"^(?!.*[\\/:*?\"<>|])[^./][^\\/:*?\"<>|\r\n]{1,254}$" # TODO revisar seguridad
RE_TAG: str = r"[\w\-\.]{1,20}"
RE_BASE64: str = r"^[A-Za-z0-9+/]{4,}={0,2}$"
RE_MIMETYPE: str = r"^[a-zA-Z0-9!#$&^_-]+/[a-zA-Z0-9!#$&^_.+-]+$"
RE_HOSTNAME: str = r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"

# Expresión regular para validar un SHA-256 en formato hexadecimal con prefijo 0x
SHA256_HEX_PATTERN = re.compile(RE_BLOCK_ID)

# Mimetypes permitidos
ALLOWED_MIMETYPES = {
    "application/pdf",
    "text/plain",
    "image/png",
    "image/jpeg",
    "application/zip",
}

# Tamaño máximo de fichero permitido
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB

# Definiciones relacionadas con erasure coding
EC_K = 3 # Repartimos fichero en 3 bloques
EC_M = 2 # Mas 2 bloques de redundancia
EC_FRAGMENT_SIZE = 1 * 1024 * 1024 # Tamanio de fragmento de 1MB
EC_BLOCK_SIZE = EC_FRAGMENT_SIZE * EC_K # Tamanio de bloque 3MB
EC_MIN_SIZE = EC_FRAGMENT_SIZE # Si el fichero es menor de 1MB simplemente clonamos

