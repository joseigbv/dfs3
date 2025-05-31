"""
Module: routes.py
Description: API route definitions for dfs3 under the /api/v1 prefix, including system status and future endpoints.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-04
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
#   2025-04-30 - José Ignacio Bravo - Initial creation

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from api.routes import auth, files, users, nodes, events
from core.constants import SOFTWARE_VERSION


# instancia de enrutador modular
router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(files.router)
router.include_router(nodes.router)
router.include_router(events.router)


@router.get("/status")
async def get_status():
    """
    Returns the current status of the dfs3 API service (testing).
    """
    return JSONResponse(content={ "status": "ok", "message": SOFTWARE_VERSION })

