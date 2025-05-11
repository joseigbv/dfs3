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

from os import path, makedirs
from fastapi import APIRouter, HTTPException, status, Depends, File, Form, UploadFile
from pydantic import ValidationError
from typing import List
from core.auth import require_auth
from core.constants import MAX_FILE_SIZE
from core.events import publish_event, build_file_created_event
from core.files import list_files
from config.settings import META_DIR, STORAGE_DIR
from api.models.files import FileEntry, UploadFileMetadata, UploadFileResponse


# instancia de enrutador modular
router = APIRouter()


@router.get("/files", response_model=List[FileEntry])
async def get_files(user_id: str = Depends(require_auth)):
    """
    Lists all files accessible to the authenticated user.
    """
    return list_files(user_id)


@router.post("/files", response_model=UploadFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    user_id: str = Depends(require_auth),
    data: UploadFile = File(...),
    metadata: str = Form(...)
):
    try:
        meta = UploadFileMetadata.parse_raw(metadata)

    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    # Ya esta validado meta
    file_id = meta.file_id

    # Crear el directorio si no existe
    makedirs(STORAGE_DIR, exist_ok=True)
    file_path = path.join(STORAGE_DIR, f"{file_id}.dat")

    # Leer y guardar archivo
    contents = await data.read()

    # Control de tamanio
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # Control de integridad
    if file_id != hashlib.sha256(contents).hexdigest():
        raise HTTPException(status_code=400, detail="file_id does not match file content")

    with open(file_path, "wb") as f:
        f.write(contents)

    # Construimos el evento y enviamos a iota / mqtt
    payload = meta.dict()
    event = build_file_created_event(payload)
    block_id = publish_event(event)

    return UploadFileResponse(status="stored")

