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

from pydantic import BaseModel, Field, constr
from typing import Literal
from datetime import datetime
from core.validators import validate_base64
from core.constants import VALID_EVENT_TYPES, RE_BLOCK_ID, RE_NODE_ID, EV_USER_REGISTERED, EV_USER_JOINED_NODE, EV_NODE_REGISTERED, EV_NODE_STATUS, EV_FILE_CREATED, EV_FILE_DELETED, EV_FILE_SHARED, EV_FILE_COPIED, EV_FILE_REPLICATED, EV_FILE_RENAMED, EV_FILE_ACCESSED


class MqttEventNotification(BaseModel):
    """
    Minimal event structure sent over MQTT to notify about a new IOTA block.
    This structure includes only the metadata necessary to fetch the full event
    from IOTA and route it by type.
    """
    block_id: constr(regex=RE_BLOCK_ID) = Field(..., description="Hexadecimal ID of the block in IOTA (with 0x prefix)")
    event_type: Literal[*VALID_EVENT_TYPES]
    timestamp: datetime
    node_id: constr(regex=RE_NODE_ID) = Field(..., description="Unique identifier of the node that emitted the event")

    class Config:
        extra = "forbid"


class BaseEvent(BaseModel):
    event_type: Literal[*VALID_EVENT_TYPES]
    timestamp: datetime
    node_id: constr(regex=RE_NODE_ID) = Field(..., description="Unique identifier of the node that emitted the event")
    protocol: str = Field(default="dfs3/1.0") # TODO: Mejorar
    signature: constr(regex=RE_BASE64)

    # Se podria usar Union[] pero es poco optimo
    payload: Dict[str, Any]

    class Config:
        extra = "forbid"

    @validator("signature")
    def validate_public_key(cls, v):
        return validate_base64(v, "signature")


# Permite parsear el payload según tipo de evento (no hay forma mas elegante)
PAYLOAD_MODELS = {
    EV_USER_REGISTERED: UserRegisteredPayload,
    EV_USER_JOINED_NODE UserJoinedNodePayload,
    EV_NODE_REGISTERED: NodeRegisteredPayload,
    EV_NODE_STATUS: NodeStatusPayload,
    EV_FILE_CREATED: FileCreatedPayload,
    #EV_FILE_DELETED,
    #EV_FILE_SHARED,
    #EV_FILE_COPIED,
    #EV_FILE_REPLICATED,
    #EV_FILE_RENAMED,
    #EV_FILE_ACCESSED
}


def parse_event(data: dict) -> BaseEvent:
    """
    Parses a raw event dict into a BaseEvent with typed payload.
    """
    event = BaseEvent(**data)
    payload_model = PAYLOAD_MODELS.get(event.event_type)
    if payload_model:
        event.payload = payload_model(**event.payload)

    return event

