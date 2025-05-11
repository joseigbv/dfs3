"""
Module: core/files.py
Description: Provides core functions for managing file metadata and entries,
including registration, linking, and handling events like file creation or sharing.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-11
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
#   2025-05-11 - José Ignacio Bravo - Initial creation

import json

from os import path, link, makedirs, listdir
from typing import List
from utils.logger import LOG, ERR
from config.settings import META_DIR, USERS_DIR
from api.models.files import FileEntry


def create(event: dict):
    """
    Creates the metadata file and user-visible entry from a file_created event payload.
    """
    try:
        # TODO: Validar el payload por seguridad !!!
        payload = event["payload"]

        file_id = payload["file_id"]
        filename = payload["filename"]
        owner = payload["owner"]

        # Guardar el JSON de metadatos, crea directorio si no existe
        makedirs(META_DIR, exist_ok=True)
        meta_path = path.join(META_DIR, f"{file_id}.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        # Ahora crea un vinculo duro entre entrada virtual y fichero metadatos
        user_dir = path.join(USERS_DIR, owner)
        makedirs(user_dir, exist_ok=True)
        entry_path = path.join(user_dir, f"{filename}")
        link(meta_path, entry_path)

        LOG(f"Registered file {filename} ({file_id}) for user {owner}")

    except Exception as e:
        ERR(f"Failed to handle file_created event: {e}")


def list_files(user_id: str) -> List[FileEntry]:
    """
    Returns the list of visible file entries for the given user by reading the virtual links
    in the user's directory and extracting metadata from the linked JSON files.
    """
    # Directorio del usuario
    user_path = path.join(USERS_DIR, user_id)
    if not path.isdir(user_path):
        return []

    entries = []

    # Listamos cada fichero
    for filename in listdir(user_path):
        full_path = path.join(user_path, filename)
        if not path.isfile(full_path):
            continue

        # Convertimos de json a diccionario
        with open(full_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Construimos FileEntry()
        entries.append(FileEntry(
            name=filename,
            file_id=meta.get("file_id", "unknown"),
            size=meta.get("size", 0),
            mimetype=meta.get("mimetype", "application/octet-stream"),
            creation_date=meta.get("creation_date", "unknown")
        ))

    return entries

