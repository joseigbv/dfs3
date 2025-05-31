"""
Module: api/routes/users.py
Description: Defines the REST API routes related to users operations in the dfs3 system.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-28
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
#   2025-05-28 - José Ignacio Bravo - Initial creation

import json

from typing import List
from pydantic import ValidationError, constr
from fastapi import APIRouter, HTTPException, Depends, Path, status
from utils.logger import LOG, ERR
from models.base import NodeEntry
from core.auth import require_auth
from core.constants import RE_USER_ID, RE_NODE_ID
from core.nodes import list_nodes, get as get_node


# instancia de enrutador modular
router = APIRouter()


@router.get("/nodes", response_model=List[NodeEntry])
async def api_get_nodes(
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Lists all nodes.
    """
    return list_nodes()


@router.get("/nodes/{node_id}", response_model=NodeEntry)
async def api_get_node(
    node_id: constr(regex=RE_NODE_ID) = Path(...), # type: ignore[valid-type]
    user_id: constr(regex=RE_USER_ID) = Depends(require_auth) # type: ignore[valid-type]
):
    """
    Devuelve informacion de un nodo identificado por su id
    """
    try:
        # Validamos que el nodo realmente exista
        if not (node := get_node(node_id)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Node not found"
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

    return node 

