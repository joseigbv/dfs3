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

from utils.logger import LOG, WRN, ERR, DBG, ABR
from config.settings import DB_FILE
from utils.db import row_to_dict
from cachetools import LRUCache, cached
from models.events import UserRegisteredEvent, UserJoinedNodeEvent


# cache de 100 elementos, se elimina el más antiguo
_user_cache: LRUCache[str, dict] = LRUCache(maxsize=100)

def invalidate_user_cache(user_id: str):
    _user_cache.pop(user_id, None)


def register(event: UserRegisteredEvent):
    """
    Stores a new user in the local database based on a user_created event.
    """
    payload = event.payload

    user_id = payload.user_id
    alias = payload.alias
    name = payload.name
    email = payload.email
    public_key = payload.public_key
    tags = ",".join(payload.tags or [])
    version = payload.version

    tstamp = int(event.timestamp.timestamp())
    creation_date = tstamp
    last_seen = tstamp

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, alias, name, email, public_key, creation_date, last_seen)
              VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, alias, name, email, public_key, creation_date, last_seen))

        conn.commit()
        conn.close()

    except Exception as e:
        ERR(f"Failed to update node from status event: {e}")


def update(event: UserJoinedNodeEvent):
    """
    Update user status in the local database based on a user_joined_node event.
    """
    payload = event.payload

    user_id = payload.user_id
    invalidate_user_cache(user_id)
    last_seen = int(event.timestamp.timestamp())

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
              SET last_seen = ? 
              WHERE user_id = ?
        """, (last_seen, user_id))

        if cursor.rowcount == 0:
            WRN(f"Node {user_id} not found in DB for update.")

        else:
            LOG(f"Node {user_id} updated with node_status info.")

        conn.commit()
        conn.close()

    except Exception as e:
        ERR(f"Failed to update node from status event: {e}")


@cached(_user_cache)
def get(user_id: str) -> dict | None:
    """
    Retrieves a user by user_id from cache or database.
    """
    # Consultamos en db si no esta en cache
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        user_data = row_to_dict(cursor, row)
        conn.close()
        return user_data

    # Si llegamos aqui, mal
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
    user = get(user_id)
    if not user:
        return None

    return user.get('public_key', None)

