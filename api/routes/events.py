"""
Module: api/routes/events.py
Description: 
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-29
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
#   2025-05-29 - José Ignacio Bravo - Initial creation

import json

from typing import List
from pydantic import ValidationError, constr
from fastapi import APIRouter, HTTPException, Depends, Path, status
from utils.logger import LOG, ERR
from models.base import EventEntry
from core.constants import RE_USER_ID, RE_BLOCK_ID
from core.auth import require_auth
from core.events import list_events, get as get_event


# instancia de enrutador modular
router = APIRouter()


# TODO filtrar por fecha, tipo de evento, ...
@router.get("/events", response_model=List[EventEntry])
async def api_get_events(
    # Sin autenticacion, informacion publica
    #user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Lists all events.
    """
    return list_events()


@router.get("/event/{block_id}", response_model=EventEntry)
async def api_get_event(
    block_id: constr(regex=RE_BLOCK_ID) = Path(...), # type: ignore[valid-type]
    # Sin autenticacion, informacion publica
    #user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Devuelve informacion de un evento identificado por su id
    """
    try:
        # Validamos que el usuario realmente exista
        if not (event := get_event(block_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
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

    return event

