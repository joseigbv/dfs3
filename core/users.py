# core/users.py

import sqlite3

from config.settings import DB_FILE
from utils.time import iso_to_epoch
from utils.db import row_to_dict
from cachetools import TTLCache


# cache de 5 minutos para un maximo de 1000 usuarios
_user_cache = TTLCache(maxsize=10, ttl=300)  


def register(event: dict):
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


def get(user_id: str) -> str | None:
    # Sin en cache, pasamos
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
    return get(user_id) is not None


def get_public_key(user_id: str) -> str | None:
    return get(user_id).get('public_key', None)

