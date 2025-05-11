"""
Module: core/users.py
Description: Core logic for managing users in the dfs3 system. Includes user lookup, key retrieval,
and caching of user data for cryptographic operations and event processing.
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
#   2025-05-08 - José Ignacio Bravo - Initial creation

import sqlite3

from config.settings import DB_FILE
from utils.time import iso_to_epoch
from utils.db import row_to_dict
from cachetools import TTLCache


# cache de 5 minutos para un maximo de 1000 usuarios
_user_cache: TTLCache[str, dict] = TTLCache(maxsize=10, ttl=300)  


def register(event: dict):
    """
    Stores a new user in the local database based on a user_created event.
    """
    node_id = event["node_id"]
    payload = event["payload"]

    user_id = payload["user_id"]
    alias = payload["alias"]
    name = payload.get("name", "")
    email = payload.get("email", "")
    public_key = payload["public_key"]

    version = payload.get("version", 1)
    tags = ",".join(payload.get("tags", []))

    # TODO: pendiente de añadir creation date y mejora errores
    creation_date = iso_to_epoch(event["timestamp"])

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, alias, name, email, public_key)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, alias, name, email, public_key))

    conn.commit()
    conn.close()


def get(user_id: str) -> dict | None:
    """
    Retrieves a user by user_id from cache or database.
    """
    # Si en cache, devolvemos
    if user_id in _user_cache:
        return _user_cache[user_id]

    # Consultamos en db
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        user_data = row_to_dict(cursor, row)
        _user_cache[user_id] = user_data
        conn.close()
        return user_data

    conn.close()
    return None


def exists(user_id: str) -> bool:
    """
    Checks whether a user with the given user_id exists in the local database.
    """
    return get(user_id) is not None


def get_public_key(user_id: str) -> str | None:
    """
    Retrieves the public key of a user by user_id from cache or database.
    """
    return get(user_id).get('public_key', None)

