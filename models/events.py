"""
Module: event.py
Description: Defines Pydantic models for dfs3 event structures, including validation for events
sent over MQTT and IOTA. Ensures type safety, field restrictions, and consistency across the system.
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

from datetime import datetime
from pydantic import BaseModel, Field, constr, conint, validator, IPvAnyAddress, EmailStr
from typing import Literal, Dict, Any, List, Optional
from models.base import StrictBaseModel
from core.validators import validate_base64
from core.constants import (
    RE_BLOCK_ID,
    RE_NODE_ID,
    RE_BASE64,
    VALID_EVENT_TYPES,
    EV_USER_REGISTERED,
    EV_USER_JOINED_NODE,
    EV_NODE_REGISTERED,
    EV_NODE_STATUS,
    EV_FILE_CREATED,
    EV_FILE_SHARED,
    EV_FILE_DELETED,
    EV_FILE_COPIED,
    EV_FILE_REPLICATED,
    EV_FILE_RENAMED,
    EV_FILE_ACCESSED,
)


# ---
# MQTT Event
# ---

class MqttEventNotification(StrictBaseModel):
    """
    Minimal event structure sent over MQTT to notify about a new IOTA block.
    This structure includes only the metadata necessary to fetch the full event
    from IOTA and route it by type.
    """
    block_id: constr(regex=RE_BLOCK_ID) = Field(...) # type: ignore[valid-type]
    event_type: Literal[*VALID_EVENT_TYPES] # type: ignore[valid-type]
    timestamp: datetime
    node_id: constr(regex=RE_NODE_ID) = Field(...) # type: ignore[valid-type]


# ---
# IOTA Event
# ---

class BaseEvent(StrictBaseModel):
    """
    Base structure for all DFS3 events, including type, origin, and payload.
    """
    event_type: Literal[*VALID_EVENT_TYPES] # type: ignore[valid-type]
    timestamp: datetime
    node_id: constr(regex=RE_NODE_ID) = Field(...) # type: ignore[valid-type]
    protocol: str = Field(default="dfs3/1.0") # TODO: Mejorar
    signature: constr(regex=RE_BASE64) # type: ignore[valid-type]

    # Se podria usar Union[] pero es poco optimo
    payload: Dict[str, Any]

    @validator("signature")
    def validate_public_key(cls, v):
        return validate_base64(v, "signature")


# ---
# IOTA File Payloads
# ---

class AuthorizedUserEntry(StrictBaseModel):
    """
    Encrypted key and IV for a user authorized to access a shared file.
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


class FileBaseEventPayload(StrictBaseModel):
    """
    Common fields for events involving user access to a specific file entry.
    """
    user_id: constr(regex=RE_USER_ID) # type: ignore[valid-type]
    file_id: constr(regex=RE_FILE_ID) # type: ignore[valid-type]
    filename: constr(regex=RE_FILENAME) # type: ignore[valid-type]


class FileCreatedEventPayload(FileBaseEventPayload):
    """
    Payload for a newly created file, including metadata, access list, and encryption info.
    """
    size: conint(ge=1, le=MAX_FILE_SIZE) # type: ignore[valid-type]
    mimetype: constr(regex=RE_MIMETYPE) # type: ignore[valid-type]
    sha256: constr(regex=RE_FILE_ID) # type: ignore[valid-type]
    iv: constr(regex=RE_BASE64) # type: ignore[valid-type]
    authorized_users: List[AuthorizedUserEntry]
    tags: Optional[List[str]] = []  # ojo
    version: conint(ge=0) = 1 # type: ignore[valid-type]

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


class FileCreatedEvent(BaseEvent):
    """
    Event indicating that a new file has been created by a user.
    """
    payload: FileCreatedEventPayload # type: ignore[assignment]


class FileSharedEventPayload(FileBaseEventPayload):
    """
    Payload for a file being shared with additional authorized users.
    """
    authorized_users: List[AuthorizedUserEntry]


class FileSharedEvent(BaseEvent):
    """
    Event indicating that a file has been shared with one or more users.
    """
    payload: FileSharedEventPayload # type: ignore[assignment]


class FileAccessedEventPayload(FileBaseEventPayload):
    """
    Payload for tracking when a user accesses a specific file entry.
    """
    pass


class FileAccessedEvent(BaseEvent):
    """
    Event indicating that a user has accessed a file entry.
    """
    payload: FileAccessedEventPayload # type: ignore[assignment]


class FileDeletedEventPayload(FileBaseEventPayload):
    """
    Payload for an event where a user deletes their virtual file entry.
    """
    pass


class FileDeletedEvent(BaseEvent):
    """
    Event indicating that a user has deleted their virtual file entry.
    """
    payload: FileDeletedEventPayload # type: ignore[assignment]


class FileRenamedEventPayload(FileBaseEventPayload):
    """
    Payload for an event where a user renames their virtual file entry.
    """
    new_name: constr(regex=RE_FILENAME) # type: ignore[valid-type]


class FileRenamedEvent(BaseEvent):
    """
    Event indicating that a user has renamed a file entry to a new name.
    """
    payload: FileRenamedEventPayload # type: ignore[assignment]


class FileReplicatedEventPayload(StrictBaseModel):
    """
    Payload for an event indicating that a file has been replicated to another node.
    """
    file_id: constr(regex=RE_FILE_ID) # type: ignore[valid-type]


class FileReplicatedEvent(BaseEvent):
    """
    Event indicating that a file has been successfully replicated.
    """
    payload: FileReplicatedEventPayload # type: ignore[assignment]


# ---
# IOTA Node Payloads
# ---

class NodeRegisteredEventPayload(StrictBaseModel):
    """
    Payload for registering a new node, including identity, platform and capacity details.
    """
    alias: constr(regex=RE_ALIAS) # type: ignore[valid-type]
    hostname: constr(regex=RE_HOSTNAME) # type: ignore[valid-type]
    public_key: constr(min_length=44, max_length=512, regex=RE_BASE64) # type: ignore[valid-type]
    platform: str
    software_version: str
    uptime: conint(ge=0) # type: ignore[valid-type]
    total_space: conint(ge=0) # type: ignore[valid-type]
    ip: IPvAnyAddress
    port: conint(ge=0, le=65535) # type: ignore[valid-type]
    tags: Optional[List[str]] = []
    version: conint(ge=0) = 1 # type: ignore[valid-type]

    @validator("public_key")
    def validate_public_key(cls, v):
        return validate_base64(v, "public_key")


class NodeRegisteredEvent(BaseEvent):
    """
    Event indicating that a new node has joined the DFS3 network.
    """
    payload: NodeRegisteredEventPayload # type: ignore[assignment]


class NodeStatusEventPayload(StrictBaseModel):
    """
    Payload for periodic status updates from a node, including uptime and available resources.
    """
    ip: IPvAnyAddress
    port: conint(ge=0, le=65535) # type: ignore[valid-type]
    uptime: conint(ge=0) # type: ignore[valid-type]
    total_space: conint(ge=0) # type: ignore[valid-type]


class NodeStatusEvent(BaseEvent):
    """
    Event indicating a heartbeat or status update from a node in the network.
    """
    payload: NodeStatusEventPayload # type: ignore[assignment]


# ---
# IOTA User Payloads
# ---

class UserRegisteredEventPayload(StrictBaseModel):
    """
    Model for registering a new user event (payload).
    """
    user_id: constr(regex=RE_USER_ID) # type: ignore[valid-type]
    alias: constr(regex=RE_ALIAS) # type: ignore[valid-type]
    name: Optional[str] = ""
    email: Optional[EmailStr] = None
    public_key: constr(min_length=44, max_length=512, regex=RE_BASE64) # type: ignore[valid-type]
    tags: Optional[List[str]] = []
    version: conint(ge=0) = 1 # type: ignore[valid-type]

    @validator("public_key")
    def validate_public_key(cls, v):
        return validate_base64(v, "public_key")


class UserRegisteredEvent(BaseEvent):
    """
    Model for registering a new user event.
    """
    payload: UserRegisteredEventPayload # type: ignore[assignment]


class UserJoinedNodeEventPayload(StrictBaseModel):
    """
    Model for verifying a signed login challenge (payload).
    """
    user_id: constr(regex=RE_USER_ID) # type: ignore[valid-type]
    challenge: str
    public_key: constr(min_length=44, max_length=512, regex=RE_BASE64) # type: ignore[valid-type]
    signature: constr(regex=RE_BASE64) # type: ignore[valid-type]

    @validator("signature")
    def validate_signature(cls, v):
        return validate_base64(v, "signature")

    @validator("public_key")
    def validate_public_key(cls, v):
        return validate_base64(v, "public_key")


class UserJoinedNodeEvent(BaseEvent):
    """
    Model for verifying a signed login challenge.
    """
    payload: UserJoinedNodeEventPayload # type: ignore[assignment]

