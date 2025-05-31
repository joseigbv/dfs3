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
from utils.crypto import verify_signature
from api.models.auth import (
    ChallengeRequest, 
    ChallengeResponse, 
    RegisterRequest, 
    RegisterResponse, 
    VerifyRequest, 
    VerifyResponse
)
from core.auth import (
    generate_challenge, 
    get_challenge, 
    create_session_token, 
    verify_session_token
)
from core.users import (
    register as register_user, 
    exists as exists_user, 
    get_public_key as get_public_key_user
)
from core.events import (
    send_user_registered_event, 
    send_user_joined_node_event
)


# instancia de enrutador modular
router = APIRouter()


@router.post("/auth/challenge", response_model=ChallengeResponse)
async def api_request_challenge(req: ChallengeRequest):
    """
    Handles a challenge request by generating and returning a unique challenge string.
    """
    if not exists_user(req.user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Generamos un challenge asociado al user y lo guardamos en cache
    challenge = generate_challenge(req.user_id)

    return ChallengeResponse(challenge=challenge)


@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def api_register(req: RegisterRequest):
    """
    Handles user registration and emits a user_created event.
    """
    if exists_user(req.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )

    # El payload del evento coincide con la solicitud api 
    payload_dict = req.dict()
    payload_dict["version"] = 1

    # Construimos y enviamos el evento 
    if not (block_id := send_user_registered_event(payload_dict)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return RegisterResponse(user_id=req.user_id)


@router.post("/auth/verify", response_model=VerifyResponse)
async def api_verify(req: VerifyRequest):
    """
    Verifies the signed challenge and returns a session token if valid.
    """
    # Deberia haber ya un challenge asociado al user_id
    if not (challenge := get_challenge(req.user_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No challenge found or expired"
        )

    # Si el usuario esta registrado, tendremos su public_key
    if not (public_key := get_public_key_user(req.user_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verificamos la firma del challenge
    if not verify_signature(public_key, challenge, req.signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this resource is forbidden"
        )

    # TODO: Por ahora, token simple de ejemplo (podemos usar UUID, JWT, etc.)
    access_token = create_session_token(req.user_id)

    # Complementamos el payload del evento usando la peticion api
    payload_dict = req.dict()
    payload_dict['challenge'] = challenge
    payload_dict['public_key'] = public_key

    # Construimos y enviamos el evento 
    if not (block_id := send_user_joined_node_event(payload_dict)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending event"
        )

    return VerifyResponse(access_token=access_token)

