"""
Module: core/auth.py
Description: Handles authentication logic for the dfs3 system, including challenge generation,
signature verification, and session token management.
Author: José Ignacio Bravo <nacho.bravo@gmail.com>
License: MIT
Created: 2025-05-01
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
#   2025-05-08 - José Ignacio Bravo - Initial creation

from base64 import b64encode
from cachetools import TTLCache
from os import urandom
from fastapi import Header, HTTPException
from utils.time import epoch_now


# cache, TTL de 5 minutos
_challenge_cache: TTLCache[str, str] = TTLCache(maxsize=10, ttl=300)  # 5 minutos
_session_tokens: TTLCache[str, str] = TTLCache(maxsize=10, ttl=1800)  # 30 minutos


def generate_challenge(user_id: str) -> str:
    """
    Generates and stores a unique login challenge for the specified user_id.
    """
    now_bytes = epoch_now().to_bytes(8, byteorder="big")
    challenge = b64encode(urandom(24) + now_bytes).decode()
    _challenge_cache[user_id] = challenge
    return challenge


def get_challenge(user_id: str) -> str | None:
    """
    Retrieves the stored login challenge for the given user_id, if it exists.
    """
    return _challenge_cache.get(user_id)


def create_session_token(user_id: str) -> str:
    """
    Generates and stores a new session token for the specified user_id.
    """
    token = b64encode(urandom(24)).decode()
    _session_tokens[token] = user_id
    return token


def verify_session_token(user_id: str, token: str) -> bool:
    """
    Verifies whether the provided session token is valid for the given user_id.
    """
    return _session_tokens.get(token) == user_id


def require_auth(authorization: str = Header(...)) -> str:
    """
    Dependency function that extracts and validates the session token from the Authorization header.
    """
    # Buscamos la cabecera Authorization: Bearer <token> ...
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    # Extraemos token de sesion y sacamos user_id
    token = authorization.removeprefix("Bearer ").strip()
    user_id = _session_tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_id

