"""
Module: api/routes/auth.py
Description: Implements the authentication routes for the dfs3 API, including login, challenge generation, and verification.
Handles user identity validation, session token creation, and event emission on successful login.
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

from fastapi import APIRouter, HTTPException, status
from api.models.auth import ChallengeRequest, ChallengeResponse, RegisterRequest, RegisterResponse, VerifyRequest, VerifyResponse
from core.auth import generate_challenge, get_challenge, create_session_token, verify_session_token
from core.users import register as register_user, exists as user_exists, get_public_key as get_user_public_key
from core.events import publish_event, build_user_registered_event, build_user_joined_node_event
from utils.crypto import verify_signature


# instancia de enrutador modular
router = APIRouter()


@router.post("/challenge", response_model=ChallengeResponse)
async def request_challenge(payload: ChallengeRequest):
    """
    Handles a challenge request by generating and returning a unique challenge string.
    """
    if not user_exists(payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")

    # Generamos un challenge asociado al user y lo guardamos en cache
    challenge = generate_challenge(payload.user_id)

    return ChallengeResponse(challenge=challenge)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    """
    Handles user registration and emits a user_created event.
    """
    if user_exists(payload.user_id):
        raise HTTPException(status_code=409, detail="User already exists")

    # Construimos el evento y enviamos a iota / mqtt
    event = build_user_registered_event(payload.dict())
    block_id = publish_event(event)

    return RegisterResponse(user_id=payload.user_id)


@router.post("/verify", response_model=VerifyResponse)
async def verify(payload: VerifyRequest):
    """
    Verifies the signed challenge and returns a session token if valid.
    """
    # Deberia haber ya un challenge asociado al user_id
    challenge = get_challenge(payload.user_id)
    if not challenge:
        raise HTTPException(status_code=400, detail="No challenge found or expired")

    # Si el usuario esta registrado, tendremos su public_key
    public_key = get_user_public_key(payload.user_id)
    if not public_key:
        raise HTTPException(status_code=404, detail="User not found")

    # Verificamos la firma del challenge
    if not verify_signature(public_key, challenge, payload.signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # TODO: Por ahora, token simple de ejemplo (podemos usar UUID, JWT, etc.)
    access_token = create_session_token(payload.user_id)

    # Vamos a generar un evento para auditoria, completamos payload
    payload_dict = payload.dict()
    payload_dict['challenge'] = challenge
    payload_dict['public_key'] = public_key

    # Construimos el evento y enviamos a iota / mqtt
    event = build_user_joined_node_event(payload_dict)
    block_id = publish_event(event)

    return VerifyResponse(access_token=access_token)

