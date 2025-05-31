"""
Module: api/models/files.py
Description: Defines Pydantic models for file-related data structures used in the DFS3 API,
including file metadata, upload and download schemas, sharing permissions, and response formats.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-10
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
#   2025-05-10 - José Ignacio Bravo - Initial creation

import re

from pydantic import BaseModel, constr, conint, validator
from typing import List, Optional
from core.validators import validate_base64
from models.base import StrictBaseModel
from core.constants import (
    RE_USER_ID, 
    RE_FILE_ID, 
    RE_FILENAME, 
    RE_TAG, 
    RE_BASE64, 
    RE_MIMETYPE, 
    ALLOWED_MIMETYPES, 
    MAX_FILE_SIZE
)


class AuthorizedUserEntry(StrictBaseModel):
    """
    Represents an authorized user who has access to a file. 
    Includes the user's ID, the encrypted symmetric key for decryption, and the initialization vector used.
    """
    user_id: constr(regex=RE_FILE_ID) # type: ignore[valid-type]
    encrypted_key: constr(regex=RE_BASE64) # type: ignore[valid-type]
    iv: constr(regex=RE_BASE64) # type: ignore[valid-type]

    @validator("iv")
    def validate_iv(cls, v):
        return validate_base64(v, "iv")

    @validator("encrypted_key")
    def validate_encrypted_key(cls, v):
        return validate_base64(v, "encrypted_key")


class UploadFileMetadata(StrictBaseModel):
    """
    Represents the metadata required when uploading an encrypted file.
    This model is used to validate and structure the JSON metadata provided in the multipart/form-data request.
    """
    filename: constr(regex=RE_FILENAME) # type: ignore[valid-type]
    file_id: constr(regex=RE_FILE_ID) # type: ignore[valid-type]
    size: conint(ge=0, le=MAX_FILE_SIZE) # type: ignore[valid-type]
    mimetype: constr(regex=RE_MIMETYPE) # type: ignore[valid-type]
    sha256: constr(regex=RE_FILE_ID) # type: ignore[valid-type]
    iv: constr(regex=RE_BASE64) # type: ignore[valid-type]
    tags: Optional[List[str]] = []
    authorized_users: List[AuthorizedUserEntry]

    @validator("mimetype")
    def validate_mimetype(cls, v):
        if v not in ALLOWED_MIMETYPES:
            raise ValueError(f"Mimetype '{v}' is not allowed")
        return v

    @validator("iv")
    def validate_iv(cls, v):
        return validate_base64(v, "iv")

    @validator("tags", each_item=True)
    def validate_tag(cls, tag):
        if not re.fullmatch(RE_TAG, tag):
            raise ValueError(f"Invalid tag: '{tag}'")
        return tag

    @validator("authorized_users")
    def check_duplicate_user_ids(cls, users):
        user_ids = [u.user_id for u in users]
        duplicates = set(uid for uid in user_ids if user_ids.count(uid) > 1)
        if duplicates:
            raise ValueError(f"Duplicate user_id(s) found: {', '.join(duplicates)}")
        return users


class StatusFileResponse(StrictBaseModel):
    """
    Defines the response returned after a file operation. 
    """
    status: str


class ShareFileRequest(StrictBaseModel):
    """
    Input model for sharing a file with authorized users.
    """
    filename: constr(regex=RE_FILENAME) # type: ignore[valid-type]
    authorized_users: List[AuthorizedUserEntry]


class RenameFileRequest(StrictBaseModel):
    """
    Input model for renaming a file.
    """
    new_name: constr(regex=RE_FILENAME) # type: ignore[valid-type]

