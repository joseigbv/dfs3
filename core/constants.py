"""
Module: constants.py
Description: Central definitions for constants and global patterns used throughout dfs3, including valid event types and SHA-256 format validation.
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

import re
from enum import IntEnum


# Utilizada para definir el nivel de logging
class Verbosity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    DEBUG = 4


# Lista global de tipos de eventos válidos en dfs3
VALID_EVENT_TYPES = {
    "user_created",
    "user_updated",
    "user_deleted",
    "user_joined_node",
    "node_registered",
    "node_unregistered",
    "node_updated",
    "node_status",
    "file_created",
    "file_deleted",
    "file_shared",
    "file_copied",
    "file_replicated",
    "file_renamed",
    "file_accessed"
}

# Version de software y de protocolo
SW_VERSION = "dfs3-node/0.1.0" 
PROTOCOL = "dfs3/1.0"

# Expresión regular para validar un SHA-256 en formato hexadecimal con prefijo 0x
SHA256_HEX_PATTERN = re.compile(r"^0x[a-fA-F0-9]{64}$")

