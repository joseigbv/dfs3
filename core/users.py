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

from typing import List
from contextlib import closing
from utils.logger import LOG, WRN, ERR, DBG, ABR
from config.settings import DB_FILE
from cachetools import LRUCache, cached
from models.base import UserEntry
from models.events import UserRegisteredEvent, UserJoinedNodeEvent


# cache de 100 elementos, se elimina el más antiguo
_user_cache: LRUCache[str, UserEntry] = LRUCache(maxsize=100)

def invalidate_user_cache(user_id: str):
    _user_cache.pop(user_id, None)


def list_users() -> List[UserEntry]:
    """
    Returns the list of users from database
    """
    with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
        cursor.execute("""
            SELECT user_id, alias, public_key
            FROM users;
        """)

        return [
            UserEntry(user_id=user_id, alias=alias, public_key=public_key)
            for user_id, alias, public_key in cursor.fetchall()
        ]


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
        with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
            cursor.execute("""
                INSERT INTO users (user_id, alias, name, email, public_key, creation_date, last_seen)
                  VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, alias, name, email, public_key, creation_date, last_seen))

            conn.commit()

        # invalidamos cache (deberia estar en None)
        invalidate_user_cache(user_id)

    except Exception as e:
        ERR(f"Failed to register node from registered event: {e}")


def update(event: UserJoinedNodeEvent):
    """
    Update user status in the local database based on a user_joined_node event.
    """
    payload = event.payload

    user_id = payload.user_id
    invalidate_user_cache(user_id)
    last_seen = int(event.timestamp.timestamp())

    try:
        with sqlite3.connect(DB_FILE) as conn, closing(conn.cursor()) as cursor:
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

    except Exception as e:
        ERR(f"Failed to update node from status event: {e}")


@cached(_user_cache, key=lambda user_id: user_id)
def get(user_id: str) -> UserEntry | None:
    """
    Retrieves a user by user_id from cache or database.
    """
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        with closing(conn.cursor()) as cursor:
            cursor.execute("""
                SELECT user_id, alias, public_key
                FROM users 
                WHERE user_id = ?
            """, (user_id,))

            return (
                UserEntry(user_id=r['user_id'], alias=r['alias'], public_key=r['public_key']) 
                if (r := cursor.fetchone()) else None
            )


def get_public_key(user_id: str) -> str | None:
    """
    Retrieves the public key of a user by user_id from cache or database.
    """
    return user.public_key if (user := get(user_id)) else None


def exists(user_id: str) -> bool:
    """
    Checks whether a user with the given user_id exists in the local database.
    """
    return (user := get(user_id)) is not None

