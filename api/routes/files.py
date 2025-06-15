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

from datetime import datetime
from pathlib import Path as OsPath
from typing import List, AsyncIterator
from pydantic import ValidationError, constr, conint
from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile, Path, Body, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from utils.time import iso_now
from utils.logger import LOG, ERR
from models.base import FileEntry
from core.auth import require_auth
from core.constants import MAX_FILE_SIZE, RE_USER_ID, RE_FILE_ID, RE_FILENAME
from core.users import get_public_key
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
    user_has_access,
    get_metadata_by_id, 
    get_metadata_by_name, 
    get_storage_path, 
    get_owner, 
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
async def api_get_files(
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Lists all files accessible to the authenticated user.
    """
    return list_files(user_id)


@router.post("/files", response_model=StatusFileResponse, status_code=status.HTTP_201_CREATED)
async def api_upload_file(
    data: UploadFile = File(...),
    metadata: str = Form(...),
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Receives an encrypted file and its associated metadata, stores the file in the local storage directory,
    and emits a file_created event for later processing by the system.
    """
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

    # Publicamos evento 
    block_id = send_file_created_event(payload_dict)
    if not block_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="stored")


@router.get("/files/{file_id}/meta")
async def api_get_file_meta(
    file_id: constr(regex=RE_FILE_ID) = Path(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Devuelve la metainformación de un fichero identificado por su id
    """
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

    except Exception as e:
        ERR(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )

    if not user_has_access(user_id, file_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # TODO crear un tipo
    return JSONResponse(content=metadata)


@router.get("/files/{file_id}/data", response_class=FileResponse)
async def api_get_file_data(
    file_id: constr(regex=RE_FILE_ID) = Path(...), # type: ignore[valid-type]
    # Para clonar, deshabilitamos auth, al fin y al cabo está cifrado !!!
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


async def try_fetch_from_node(node_id: str, file_id: str) -> AsyncIterator[bytes] | None:
    """
    Funcion auxiliar aync para hacer de proxy y solicitar el fichero a otro nodo.
    """
    if (url := get_file_url_for_node(node_id, file_id)):
        try:
            # TODO ajustar timeout
            async with httpx.AsyncClient(timeout=5.0) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_bytes():
                            yield chunk

        except Exception as e:
            ERR(e)

    # Si llegamos, mal
    return


async def fetch_wrapper(node_id: str, file_id: str) -> AsyncIterator[bytes] | None:
    stream = try_fetch_from_node(node_id, file_id)
    try:
        # Intentamos obtener el primer chunk para validar que responde
        first_chunk = await anext(stream)

        # Generamos un nuevo iterador que devuelve ese chunk y el resto
        async def re_yield():
            yield first_chunk
            async for chunk in stream:
                yield chunk

        return re_yield()

    except Exception:
        return None


async def stream_and_store(source_stream: AsyncIterator[bytes], local_path: OsPath, file_id: str) -> AsyncIterator[bytes]:
    """
    Recibe un stream de bytes y lo envía al cliente mientras lo guarda localmente.
    """
    async with aiofiles.open(local_path, "wb") as f:
        async for chunk in source_stream:
            await f.write(chunk)
            yield chunk

    # Ahora generamos evento para informar al resto de nodos
    if (block_id := send_file_replicated_event({"file_id": file_id})):
        LOG(f"File {file_id} successfully cloned")
    else:
        ERR(f"Error sending file_replicated event for {file_id}")


async def file_streamer(path, chunk_size=8192):
    """
    Descarga de fichero por bloques, implementado por problemas de rendimiento
    Mejora la velocidad de 15s a 270ms (descontando registro IOTA)
    """
    async with aiofiles.open(path, "rb") as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            yield chunk


@router.get("/files/{filename}", response_class=StreamingResponse)
async def api_download_file(
    filename: constr(regex=RE_FILENAME) = Path(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Descarga un fichero cifrado identificado por filename y devuelve los metadatos 
    necesarios para su descifrado como cabeceras http
    """
    try:
        # Validamos que el fichero realmente exista
        _, metadata = get_metadata_by_name(user_id, filename)

        # Extraemos la metainformacion necesaria para descifrarlo
        file_id = metadata["file_id"]
        owner = metadata["owner"]
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

    except Exception as e:
        ERR(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )

    if not user_has_access(user_id, file_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Clave publica del propietario del fichero (necesaria)
    # TODO Incorporar a metadatos de fichero para simplificar
    owner_public_key = get_public_key(owner)

    # Clave criptografica para user_id
    if not (result := get_user_crypto(user_id, file_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    encrypted_key, iv_key = result

    # Construimos el payload del evento a partir de la peticion api
    payload_dict = {
        "user_id": user_id,
        "file_id": file_id,
        "filename": filename
    }

    # Publicamos evento de auditoria
    if not (block_id := send_file_accessed_event(payload_dict)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    # Tanto si tenemos el fichero, como si hay que pedirlo, misma cabecera
    headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-DFS3-File-ID": file_id,
        "X-DFS3-Owner": owner,
        "X-DFS3-Public-Key": owner_public_key,
        "X-DFS3-Size": str(size),
        "X-DFS3-IV": iv,
        "X-DFS3-SHA256": sha256,
        "X-DFS3-Mimetype": mimetype,
        "X-DFS3-Encrypted-Key": encrypted_key,
        "X-DFS3-IV-Key": iv_key
    }

    # Ahora devolvemos datos si los tenemos en local
    storage_path = get_storage_path(file_id)
    if storage_path.is_file():
        return StreamingResponse(
            file_streamer(storage_path),
            media_type="application/octet-stream",
            headers=headers
        )

    # No esta en local, vamos a probar con las replicas
    if not (replica_nodes := metadata.get("replica_nodes")):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Lanzamos peticiones en paralelo para cada nodo ...
    tasks = [
        asyncio.create_task(fetch_wrapper(node, file_id)) 
        for node in replica_nodes
    ]

    # ... hasta que responda uno
    for task in asyncio.as_completed(tasks):
        if (stream := await task):
            # Cancelar las tareas restantes
            for t in tasks:
                if t is not task:
                    t.cancel()

            # Actuamos como proxy, guardando una copia local
            return StreamingResponse(
                stream_and_store(stream, storage_path, file_id),
                media_type="application/octet-stream",
                headers=headers
            )

    # si llegamos aqui, mal
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="File not found"
    )


@router.post("/files/share", response_model=StatusFileResponse)
async def api_share_file(
    req: ShareFileRequest = Body(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Comparte fichero con otro usuario y añade la información criptografica necesaria
    para que este pueda descifrarlo.
    """
    try:
        # Validamos que el fichero realmente exista
        _, metadata = get_metadata_by_name(user_id, req.filename)
        file_id = metadata["file_id"]
        owner = metadata["owner"]

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

    except Exception as e:
        ERR(e)
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
    if not (block_id := send_file_shared_event(payload_dict)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="shared")


@router.delete("/files/{filename}", response_model=StatusFileResponse)
async def api_delete_file(
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

    except Exception as e:
        ERR(e)
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
    if not (block_id := send_file_deleted_event(payload_dict)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="deleted")


@router.patch("/files/{filename}", response_model=StatusFileResponse)
async def api_rename_file(
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

    except Exception as e:
        ERR(e)
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
    if not (block_id := send_file_renamed_event(payload_dict)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return StatusFileResponse(status="renamed")


@router.get("/files/{file_id}/block/{block}/fragment/{fragment}")
async def api_get_fragment(
    file_id: constr(regex=RE_FILE_ID) = Path(...), # type: ignore[valid-type]
    block: conint(ge=0) = Path(...), # type: ignore[valid-type]
    fragment: conint(ge=0) = Path(...) # type: ignore[valid-type]
):
    """
    Extrae un fragmento erasure code del fichero identificado por file_id.
    """
    # TODO pendiente...
    pass

