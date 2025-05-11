"""
Module: api/models/auth.py
Description: Defines request and response models for authentication endpoints in the dfs3 API.
Includes schemas for login, challenge-response, and user verification logic.
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

from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional
from core.constants import RE_USER_ID, RE_ALIAS, RE_BASE64
from core.validators import validate_base64


class RegisterRequest(BaseModel):
    """
    Request model for registering a new user.
    """
    user_id: constr(regex=RE_USER_ID)
    alias: constr(regex=RE_ALIAS)
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    public_key: constr(min_length=44, max_length=512, regex=RE_BASE64)

    class Config:
        extra = "forbid"

    @validator("public_key")
    def validate_public_key(cls, v):
        return validate_base64(v, "public_key")


class RegisterResponse(BaseModel):
    """
    Response model returned after a successful user registration.
    """
    user_id: str


class ChallengeRequest(BaseModel):
    """
    Request model for initiating a login challenge using a user ID.
    """
    user_id: constr(regex=RE_USER_ID)

    class Config:
        extra = "forbid"


class ChallengeResponse(BaseModel):
    """
    Response model containing the generated login challenge and timestamp.
    """
    challenge: str


class VerifyRequest(BaseModel):
    """
    Request model for verifying a signed login challenge.
    """
    user_id: constr(regex=RE_USER_ID)
    signature: constr(regex=RE_BASE64)

    class Config:
        extra = "forbid"

    @validator("signature")
    def validate_public_key(cls, v):
        return validate_base64(v, "signature")


class VerifyResponse(BaseModel):
    """
    Response model returned after successful challenge verification, includes session token.
    """
    access_token: str

