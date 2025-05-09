"""
Module: db_init.py
Description: Creates SQLite database and tables for dfs3 if not present.
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

import sqlite3
import os

from utils.logger import LOG, WRN, ERR, DBG, Verbosity
from config.settings import DATA_DIR, DB_FILE


def create_db():
    """
    Creates the SQLite database and all required tables if they do not already exist.

    This includes the 'users', 'nodes', 'files', and 'entries' tables. If the database file
    already exists, the function will emit a warning and do nothing.
    """

    # Si no existe la db, la creamos
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_FILE):
        LOG(f"Database '{DB_FILE}' already exists")
        return

    WRN(f"Database '{DB_FILE}' doesn't exist, creating...")

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Tabla de usuarios
        cursor.execute('''
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            alias TEXT NOT NULL,
            name TEXT,
            email TEXT,
            public_key TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            version INTEGER DEFAULT 1 
        )
        ''')

        # Tabla de nodos
        cursor.execute('''
        CREATE TABLE nodes (
            node_id TEXT PRIMARY KEY,
            alias TEXT, 
            hostname TEXT,
            version INTEGER NOT NULL,
            public_key TEXT NOT NULL,
            platform TEXT,
            software_version TEXT,
            uptime INTEGER NOT NULL,
            total_space INTEGER DEFAULT 0,
            ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            tags TEXT,
            creation_date TIMESTAMP NOT NULL, 
            last_seen TIMESTAMP NOT NULL
        )
        ''')

        # Tabla de ficheros
        cursor.execute('''
        CREATE TABLE files (
            file_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            size INTEGER,
            created_at TEXT,
            modified_at TEXT,
            md5_original TEXT,
            mimetype TEXT,
            tags TEXT DEFAULT '[]',
            replica_nodes TEXT DEFAULT '[]',
            encrypted_keys TEXT,
            version INTEGER DEFAULT 1,
            FOREIGN KEY (owner_id) REFERENCES users(user_id)
        )
        ''')

        # Tabla de entradas
        cursor.execute('''
        CREATE TABLE entries (
            user_id TEXT NOT NULL,
            file_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            PRIMARY KEY (user_id, filename),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (file_id) REFERENCES files(file_id)
        )
        ''')

        conn.commit()
        conn.close()

        LOG(f"Database '{DB_FILE}' created successfully.", level=Verbosity.LOW)

    except Exception as e:
        ERR(f"Failed to create database: {str(e)}")

