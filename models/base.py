"""
Module: models/ base.py
Description: 
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-22
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
#   2025-05-22 - José Ignacio Bravo - Initial creation

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, constr, conint, validator
from core.validators import validate_base64
from core.constants import (
    RE_NODE_ID,
    RE_FILE_ID,
    RE_USER_ID,
    RE_BLOCK_ID,
    RE_FILENAME,
    RE_BASE64,
    RE_MIMETYPE,
    RE_ALIAS,
    VALID_EVENT_TYPES,
    MAX_FILE_SIZE
)


class StrictBaseModel(BaseModel):
    """
    Para evitar tener que añadir extra = "forbit" al resto de clases 
    """
    class Config:
        extra = "forbid"


class FileEntry(StrictBaseModel):
    file_id: constr(regex=RE_FILE_ID) = Field(...) # type: ignore[valid-type]
    name: constr(regex=RE_FILENAME) = Field(...) # type: ignore[valid-type]
    size: conint(ge=0, le=MAX_FILE_SIZE) = Field(...) # type: ignore[valid-type]
    mimetype: constr(regex=RE_MIMETYPE) = Field(...) # type: ignore[valid-type]
    creation_date: str = Field(...) # TODO pendiente de estudiar


class UserEntry(StrictBaseModel):
    user_id: constr(regex=RE_USER_ID) = Field(...) # type: ignore[valid-type]
    alias: constr(regex=RE_ALIAS) = Field(...) # type: ignore[valid-type]
    public_key: constr(min_length=44, max_length=512, regex=RE_BASE64) = Field(...) # type: ignore[valid-type]

    @validator("public_key")
    def validate_public_key(cls, v):
        return validate_base64(v, "public_key")


class NodeEntry(StrictBaseModel):
    node_id: constr(regex=RE_NODE_ID) = Field(...) # type: ignore[valid-type]
    alias: constr(regex=RE_ALIAS) = Field(...) # type: ignore[valid-type]
    public_key: constr(min_length=44, max_length=512, regex=RE_BASE64) = Field(...) # type: ignore[valid-type]

    @validator("public_key")
    def validate_public_key(cls, v):
        return validate_base64(v, "public_key")


class EventEntry(StrictBaseModel):
    """
    Minimal event structure sent over MQTT to notify about a new IOTA block.
    """
    timestamp: datetime = Field(...) # type: ignore[valid-type]
    block_id: constr(regex=RE_BLOCK_ID) = Field(...) # type: ignore[valid-type]
    event_type: Literal[*VALID_EVENT_TYPES] # type: ignore[valid-type]
    node_id: constr(regex=RE_NODE_ID) = Field(...) # type: ignore[valid-type]


