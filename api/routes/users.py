"""
Module: api/routes/users.py
Description: Defines the REST API routes related to users operations in the dfs3 system.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-27
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
#   2025-05-27 - José Ignacio Bravo - Initial creation

import json

from typing import List
from pydantic import ValidationError, constr
from fastapi import APIRouter, HTTPException, Depends, Path, status
from utils.logger import LOG, ERR
from models.base import UserEntry
from core.constants import RE_USER_ID
from core.auth import require_auth
from core.users import list_users, get as get_user


# instancia de enrutador modular
router = APIRouter()


@router.get("/users", response_model=List[UserEntry])
async def api_get_users(
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Lists all users.
    """
    return list_users()


@router.get("/users/{user_id_}", response_model=UserEntry)
async def api_get_user(
    user_id_: constr(regex=RE_USER_ID) = Path(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Devuelve informacion de un usuario identificado por su id
    """
    try:
        # Validamos que el usuario realmente exista
        if not (user := get_user(user_id_)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
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

    return user

