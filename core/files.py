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
import os
import hashlib
import requests

from pathlib import Path
from typing import List, Tuple
from cachetools import LRUCache, cached
from utils.logger import LOG, WRN, ERR, ABR
from config.settings import STORAGE_DIR, META_DIR, USERS_DIR
from core import context
from core.constants import MAX_FILE_SIZE, EC_MIN_SIZE
from core.nodes import get as get_node, should_clone_from
from core.events import send_file_replicated_event
from models.base import FileEntry
from models.events import (
    FileCreatedEvent, 
    FileSharedEvent,
    FileAccessedEvent,
    FileRenamedEvent,
    FileDeletedEvent,
    FileReplicatedEvent
)


# Tamaño de la caché: puedes ajustarlo según el uso esperado (ej. 100 ficheros)
_metadata_cache: LRUCache[str, Tuple[Path, dict]] = LRUCache(maxsize=100)
_file_id_cache: LRUCache[Tuple[str, str], str] = LRUCache(maxsize=100)

def invalidate_metadata_cache(file_id: str):
    _metadata_cache.pop(file_id, None)


def get_available_filename_path(user_id: str, desired_name: str) -> Path:
    """
    Returns a path for a filename that does not exist in the specified directory.
    If 'document.pdf' exists, returns 'document(1).pdf', 'document(2).pdf', etc.
    """
    name, ext = os.path.splitext(desired_name)
    user_dir = get_user_dir(user_id)
    candidate = user_dir / desired_name
    counter = 1

    while candidate.exists():
        candidate = user_dir / f"{name} ({counter}){ext}"
        counter += 1

    return candidate


def get_file_url_for_node(node_id: str, file_id: str) -> str | None:
    """
    Construimos la peticion de file_id a partir del id del nodo propietario
    Debe ser accesible para el resto de nodos a traves de su ip:puerto
    """
    if not (node := get_node(node_id)):
        return None

    # TODO: Mejorar URL de peticion, para pruebas vale
    ip, port = node["ip"], node["port"]

    return f"http://{ip}:{port}/api/v1/files/{file_id}/data"


def clone(node_id: str, file_id: str) -> bool:
    """
    Clona un fichero cifrado desde otro nodo remoto y lo guarda localmente.
    """
    try:
        if not (url := get_file_url_for_node(node_id, file_id)):
            ERR(f"URL info not found for {node_id}")
            return False

        # TODO: Convertimos en async ???
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            ERR(f"Failed to download {file_id} from {node_id}: {response.status_code}")
            return False

        # Control de tamanio
        if len(response.content) > MAX_FILE_SIZE:
            ERR(f"File {file_id} too large")
            return False

        # Control de integridad
        if file_id != hashlib.sha256(response.content).hexdigest():
            ERR(f"Invalid file content {file_id}")
            return False

        # Si hemos llegado aqui, almacenamos en local
        file_path = get_storage_path(file_id)
        with file_path.open("wb") as f:
            f.write(response.content)

        # Ahora generamos evento para informar al resto de nodos
        if not (block_id := send_file_replicated_event({"file_id": file_id})):
            ERR(f"Error sending file_replicated event for {file_id}")
            return False

        LOG(f"File {file_id} successfully cloned from {node_id}")

    except Exception as e:
        ERR(f"Error cloning {file_id} from {node_id}: {e}")
        return False

    # si llegamos, bien
    return True


def replicate(event: FileReplicatedEvent):
    """
    Actualiza los metadatos de un fichero con un nueva nueva replica completa.
    """
    try:
        node_id = event.node_id
        file_id = event.payload.file_id

        # Actualizamos fichero con metadatos
        _, metadata = get_metadata_by_id(file_id)
        if node_id not in metadata["replica_nodes"]:
            metadata["replica_nodes"].append(node_id)
            save_metadata(file_id, metadata)

        LOG(f"Update replicas of file {file_id}, add node {node_id}")

    except Exception as e:
        ERR(f"Failed to handle file_replicated event: {e}")


def create(event: FileCreatedEvent):
    """
    Creates the metadata file and user-visible entry from a filecreated event payload.
    """
    try:
        node_id = event.node_id
        payload = event.payload 
        timestamp = event.timestamp

        user_id = payload.user_id
        file_id = payload.file_id
        filename = payload.filename
        size = payload.size

        # Adaptamos estructura a partir de payload 
        metadata = payload.dict()
        metadata["owner"] = user_id
        del metadata["user_id"]
        del metadata["filename"]
        metadata["creation_date"] = timestamp.isoformat()
        metadata["replica_nodes"] = [node_id]
        metadata["version"] = 1

        # TODO: Pendiente crear un modelo para metadatos de fichero
        # ...

        # Guardar el JSON de metadatos, crea directorio si no existe
        meta_path = save_metadata(file_id, metadata)

        # Ahora crea un vinculo duro entre entrada virtual y fichero metadatos
        entry_path = get_available_filename_path(user_id, filename)
        entry_path.hardlink_to(meta_path)

        # invalidamos cache, deberia estar a none
        invalidate_metadata_cache(file_id)

        LOG(f"Registered file {filename} ({file_id}) for user {user_id}")

        # Ahora clonamos si el fichero es pequeño y nuestro nodo es candidato
        if (
            size < EC_MIN_SIZE 
            and should_clone_from(node_id, size) 
            and context.config.get('status') != 'syncing'
        ):
            clone(node_id, file_id)

    except Exception as e:
        ABR(f"Failed to handle file_created event: {e}")


def share(event: FileSharedEvent):
    """
    Modify the metadata file and create a user-visible entry from a file_shared event payload.
    """
    try:
        payload = event.payload 

        user_id = payload.user_id
        file_id = payload.file_id
        filename = payload.filename

        # Fusionamos authorized_users nuevo con el que hay en metadata
        meta_path, metadata = get_metadata_by_id(file_id)
        authorized_users = {u["user_id"]: u for u in metadata["authorized_users"]}

        for user in payload.authorized_users:
            authorized_users[user.user_id] = user.dict()

            # creamos una entrada virtual apuntando al fichero metadatos para cada usuario
            entry_path = get_available_filename_path(user.user_id, filename)
            entry_path.hardlink_to(meta_path)

            LOG(f"Shared file {filename} ({file_id}) with user {user.user_id}")

        # Reconstruimos la lista final de usuarios autorizados y salvamos
        metadata["authorized_users"] = list(authorized_users.values())
        save_metadata(file_id, metadata)

    except Exception as e:
        ERR(f"Failed to handle file_shared event: {e}")


def rename(event: FileRenamedEvent):
    """
    Rename a user-visible entry from a file_renamed event payload.
    """
    try:
        payload = event.payload 

        user_id = payload.user_id
        file_id = payload.file_id
        filename = payload.filename
        new_name = payload.new_name

        # Renombramos a un nombre de fichero disponible (ej. document (1).pdf)
        file, _ = get_metadata_by_name(user_id, filename)
        file.rename(get_available_filename_path(user_id, new_name))

        LOG(f"Renamed file {filename} to {new_name} ({file_id}) with user {user_id}")

    except Exception as e:
        ERR(f"Failed to handle file_renamed event: {e}")


def delete(event: FileDeletedEvent):
    """
    Delete a user-visible entry from a file_deleted event payload.
    """
    try:
        payload = event.payload 

        user_id = payload.user_id
        file_id = payload.file_id
        filename = payload.filename

        # TODO: Pendiente borrar fichero 'real' (si aplica)
        file, _ = get_metadata_by_name(user_id, filename)
        file.unlink()

        LOG(f"Deleted file {filename} ({file_id}) with user {user_id}")

    except Exception as e:
        ERR(f"Failed to handle file_deleted event: {e}")


def list_files(user_id: str) -> List[FileEntry]:
    """
    Returns the list of visible file entries for the given user by reading the virtual links
    in the user's directory and extracting metadata from the linked JSON files.
    """
    user_path = get_user_dir(user_id)
    entries = []

    # Listamos cada fichero
    for entry in user_path.iterdir():
        if not entry.is_file():
            continue

        # Convertimos de json a diccionario
        with entry.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Construimos FileEntry()
        entries.append(FileEntry(
            name=entry.name,
            file_id=metadata["file_id"],
            size=metadata.get("size", 0),
            mimetype=metadata.get("mimetype", "application/octet-stream"),
            creation_date=metadata.get("creation_date", "unknown")
        ))

    return entries


def get_storage_path(file_id: str) -> Path:
    """
    Devuelve la ruta completa del fichero de datos para file_id
    Si no existe la ruta, la crea
    """
    storage_dir = Path(STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)

    return storage_dir / f"{file_id}.dat"


def get_meta_path(file_id: str) -> Path:
    """
    Devuelve la ruta completa del fichero de metadatos para file_id
    Si no existe la ruta, la crea
    """
    meta_dir = Path(META_DIR)
    meta_dir.mkdir(parents=True, exist_ok=True)

    return meta_dir / f"{file_id}.json"


@cached(_metadata_cache, key=lambda file_id: file_id)
def get_metadata_by_id(file_id: str) -> Tuple[Path, dict]:
    """
    Devuelve los metadatos de un fichero a partir de su file_id.
    Usa caché LRU para evitar lecturas redundantes del disco.
    """
    meta_path = get_meta_path(file_id)
    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata for file_id {file_id} not found")

    with meta_path.open("r", encoding="utf-8") as f:
        return meta_path, json.load(f)


def get_metadata_by_name(user_id: str, filename: str) -> Tuple[Path, dict]:
    """
    Devuelve los metadatos de un fichero a partir de su nombre.
    """
    # Para evitar path traversal
    user_dir = get_user_dir(user_id).resolve()
    user_path = (user_dir / filename).resolve()
    if not str(user_path).startswith(str(user_dir)):
        raise ValueError("Path traversal detected")

    # Existe el fichero?
    if not user_path.exists():
        raise FileNotFoundError(f"Metadata for {user_id} and {filename} not found")

    with user_path.open("r", encoding="utf-8") as f:
        return user_path, json.load(f)


@cached(_file_id_cache)
def get_file_id_by_name(user_id: str, filename: str) -> str:
    """
    Devuelve el file_id de un filename para un user_id.
    Usa caché LRU para evitar lecturas redundantes a disco.
    """
    _, metadata = get_metadata_by_name(user_id, filename)

    return metadata["file_id"]


def save_metadata(file_id: str, metadata: dict) -> Path:
    """
    Guardar el JSON de metadatos en un fichero
    """
    invalidate_metadata_cache(file_id)
    meta_path = get_meta_path(file_id)

    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return meta_path


def get_user_dir(user_id: str) -> Path:
    """
    Devuelve la ruta del usuario en el filesystem real, si no existe la crea
    """
    user_dir = Path(USERS_DIR) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    return user_dir


def get_owner(file_id: str) -> str:
    """
    Devuelve el propietario de un fichero identificado por file_id
    """
    _, metadata = get_metadata_by_id(file_id)

    return metadata['user_id']


def get_user_crypto(user_id, file_id) -> Tuple[str, str] | None:
    """
    Obtener datos de descifrado para este usuario.
    """ 
    _, metadata = get_metadata_by_id(file_id)
    authorized_users = metadata.get("authorized_users", [])

    return next(
        ((u['encrypted_key'], u['iv']) for u in authorized_users if u["user_id"] == user_id), 
        None
    )


def user_has_access(user_id, file_id) -> bool:
    """
    Verifica si un usuario tiene acceso a un archivo determinado según los metadatos.
    """
    return get_user_crypto(user_id, file_id) != None

