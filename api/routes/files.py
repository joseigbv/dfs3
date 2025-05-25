"""
Module: api/routes/files.py
Description: Defines the REST API routes related to file operations in the dfs3 system. Includes endpoints
for uploading, downloading, deleting, sharing, and renaming files, as well as managing file visibility.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-09
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
#   2025-05-09 - José Ignacio Bravo - Initial creation

import hashlib
import json
import asyncio
import aiofiles
import httpx

from pathlib import Path as OsPath
from typing import List, AsyncIterator
from pydantic import ValidationError, constr
from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile, Path, Body, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from utils.time import iso_now
from utils.logger import LOG, ERR
from models.base import FileEntry
from core import context
from core.auth import require_auth
from core.constants import MAX_FILE_SIZE, RE_USER_ID, RE_FILE_ID, RE_FILENAME
from core.events import (
    send_file_created_event, 
    send_file_shared_event, 
    send_file_accessed_event,
    send_file_deleted_event,
    send_file_renamed_event,
    send_file_replicated_event
)
from core.files import (
    list_files, 
    get_metadata_by_id, 
    get_metadata_by_name, 
    get_storage_path, 
    get_owner, 
    user_has_access,
    get_file_id_by_name,
    get_file_url_for_node,
    get_user_crypto
)
from api.models.files import (
    UploadFileMetadata, 
    StatusFileResponse, 
    ShareFileRequest,
    RenameFileRequest
)


# instancia de enrutador modular
router = APIRouter()


@router.get("/files", response_model=List[FileEntry])
async def get_files(
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Lists all files accessible to the authenticated user.
    """
    return list_files(user_id)


@router.post("/files", response_model=StatusFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    data: UploadFile = File(...),
    metadata: str = Form(...),
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Receives an encrypted file and its associated metadata, stores the file in the local storage directory,
    and emits a file_created event for later processing by the system.
    """
    if not context.config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid context config"
        )

    try:
        # Aqui metadata viene como un string json
        meta = UploadFileMetadata.parse_raw(metadata)

    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )
        
    # Leer y guardar archivo
    contents = await data.read()

    # Control de tamanio
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large"
        )

    # Control de integridad
    if meta.file_id != hashlib.sha256(contents).hexdigest():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file content"
        )

    # Si hemos llegado, guardamos el contenido
    storage_path = get_storage_path(meta.file_id)
    with storage_path.open("wb") as f:
        f.write(contents)

    # Construimos el payload del evento complementando la peticion web
    payload_dict = meta.dict()
    payload_dict["user_id"] = user_id
    payload_dict["creation_date"] = iso_now()
    payload_dict["replica_nodes"] = [context.config["node_id"]]
    payload_dict["version"] = 1

    # Publicamos evento 
    block_id = send_file_created_event(payload_dict)
    if not block_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="stored")


async def try_fetch_from_node(node_id: str, file_id: str) -> httpx.Response | None:
    """
    Funcion auxiliar aync para hacer de proxy y solicitar el fichero a otro nodo.
    """
    url = get_file_url_for_node(node_id, file_id)
    if not url:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, stream=True) # type: ignore
            if response.status_code == 200:
                return response

    except Exception:
        pass

    # Si llegamos, mal
    return None


async def stream_and_store(source_stream: AsyncIterator[bytes], local_path: OsPath, file_id: str) -> AsyncIterator[bytes]:
    """
    Recibe un stream de bytes y lo envía al cliente mientras lo guarda localmente.
    """
    async with aiofiles.open(local_path, "wb") as f:
        async for chunk in source_stream:
            await f.write(chunk)
            yield chunk  # Enviar al cliente

    # Ahora generamos evento para informar al resto de nodos
    block_id = send_file_replicated_event({"file_id": file_id})
    if not block_id:
        ERR(f"Error sending file_replicated event for {file_id}")

    else:
        LOG(f"File {file_id} successfully cloned")


@router.get("/files/{filename}")
async def download_file(
    filename: constr(regex=RE_FILE_ID) = Path(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    try:
        # Validamos que el fichero realmente exista
        _, metadata = get_metadata_by_name(user_id, filename)

        # Y extraemos la metainformacion necearia para descifrarlo
        file_id = metadata["file_id"]
        size = metadata["size"]
        iv = metadata["iv"]
        sha256 = metadata["sha256"]
        mimetype = metadata["mimetype"]

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )

    if not user_has_access(user_id, file_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    result = get_user_crypto(user_id, file_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    encrypted_key, iv_key = result

    payload_dict = {
        "user_id": user_id,
        "file_id": file_id,
        "filename": filename
    }

    # Publicamos evento de auditoria
    block_id = send_file_accessed_event(payload_dict)
    if not block_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": size,
        "X-DFS3-File-ID": file_id,
        "X-DFS3-Size": size,
        "X-DFS3-IV": iv,
        "X-DFS3-SHA256": sha256,
        "X-DFS3-Mimetype": mimetype,
        "X-DFS3-Encrypted-Key": encrypted_key,
        "X-DFS3-IV-Key": iv_key
    }

    # Ahora devolvemos datos si los tenemos en local
    storage_path = get_storage_path(file_id)
    if storage_path.is_file():
        f = await aiofiles.open(storage_path, "rb")
        return StreamingResponse(
            f,
            media_type="application/octet-stream",
            headers=headers
        )

    # No esta en local, vamos a probar con las replicas
    replica_nodes = metadata.get("replica_nodes")
    if not replica_nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Lanzamos peticiones en paralelo para cada nodo hasta que responda uno
    tasks = [asyncio.create_task(try_fetch_from_node(node, file_id)) for node in replica_nodes]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in done:
        # Si ha contestado algun nodo con la replica
        response = task.result()
        if response:
            # Cancelamos el resto de tareas pendientes
            for t in pending:
                t.cancel()

            # Y actuamos como proxy, guardando una copia local
            return StreamingResponse(
                stream_and_store(response.aiter_bytes(), storage_path, file_id),
                media_type="application/octet-stream",
                headers=headers
            )

    # si llegamos aqui, mal
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="File not found"
    )


@router.get("/files/{file_id}/meta")
async def get_file_meta(
    file_id: constr(regex=RE_FILE_ID) = Path(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    try:
        # Validamos que el fichero realmente exista
        _, metadata = get_metadata_by_id(file_id)

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )

    if not user_has_access(user_id, file_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return JSONResponse(content=metadata)


@router.get("/files/{file_id}/data", response_model=FileResponse)
async def get_file_data(
    file_id: constr(regex=RE_FILE_ID) = Path(...), # type: ignore[valid-type]
    # Para clonar, deshabilitamos auth, al fin y al cabo está cifrado !!!
    #user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Retrieves and returns the encrypted content of a file identified by its file_id, 
    if the requesting user is authorized to access it.
    """
    storage_path = get_storage_path(file_id)
    if not storage_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return FileResponse(
        path=str(storage_path), 
        media_type="application/octet-stream", 
        filename=file_id
    )


@router.post("/files/share", response_model=StatusFileResponse)
async def share_file(
    req: ShareFileRequest = Body(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    try:
        # Validamos que el fichero realmente exista
        _, metadata = get_metadata_by_name(user_id, req.filename)
        file_id = metadata["file_id"]
        owner = metadata["user_id"]

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="File not found"
        )

    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )

    # Validamos que user_id sea el propietario
    if owner != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Construimos el payload del evento a partir de la peticion api, complementándolo
    payload_dict = req.dict()
    payload_dict["user_id"] = user_id
    payload_dict["file_id"] = file_id

    # Publicamos evento 
    block_id = send_file_shared_event(payload_dict)
    if not block_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="shared")


@router.delete("/files/{filename}")
async def delete_file_entry(
    filename: constr(regex=RE_FILENAME) = Path(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Elimina una entrada virtual (nombre visible) del usuario autenticado.
    No borra el archivo físico si está compartido o tiene otras entradas.
    """
    try:
        # Validamos que el fichero realmente exista
        file_id = get_file_id_by_name(user_id, filename)

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )

    # Deberia tener permisos
    if not user_has_access(user_id, file_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Construimos el payload del evento a partir de la peticion api
    payload_dict = {
        "user_id": user_id,
        "file_id": file_id,
        "filename": filename
    }

    # Publicamos evento 
    block_id = send_file_deleted_event(payload_dict)
    if not block_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="deleted")


@router.patch("/files/{filename}")
async def rename_file_entry(
    filename: constr(regex=RE_FILENAME) = Path(...), # type: ignore[valid-type]
    req: RenameFileRequest = Body(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Renombra una entrada virtual (nombre visible) del usuario autenticado.
    """
    try:
        # Validamos que el fichero realmente exista
        file_id = get_file_id_by_name(user_id, filename)
        new_name = req.new_name

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )

    # Deberia tener permisos
    if not user_has_access(user_id, file_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Construimos el payload del evento a partir de la peticion api
    payload_dict = {
        "user_id": user_id,
        "file_id": file_id,
        "filename": filename,
        "new_name": new_name
    }

    # Publicamos evento 
    block_id = send_file_renamed_event(payload_dict)
    if not block_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="renamed")


@router.get("/files/{file_id}/block/{block}/fragment/{fragment}")
async def get_fragment(
    file_id: constr(regex=RE_FILE_ID) = Path(...), # type: ignore[valid-type]
    block: conint(ge=0) = Path(...), # type: ignore[valid-type]
    fragment: conint(ge=0) = Path(...) # type: ignore[valid-type]
):
    # Pendiente...
    pass

    # fragment_path = get_fragment_path(file_id, block_id, fragment_id)
    #if not fragment_path.exists():
    #    raise HTTPException(status_code=404, detail="Fragment not found")
    #return FileResponse(
    #    fragment_path,
    #    media_type="application/octet-stream",
    #    headers={
    #        "X-Block-ID": block,
    #        "X-Fragment-ID": fragment,
    #        "X-File-ID": file_id
    #    }
    #)

