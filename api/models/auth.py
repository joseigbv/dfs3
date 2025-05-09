# api/models/auth.py

# =============================================================
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
# =============================================================

from core.constants import RE_USER_ID, RE_ALIAS
from core.validators import validate_base64
from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional

import base64


class RegisterRequest(BaseModel):
    user_id: constr(regex=RE_USER_ID) = ...
    alias: constr(regex=RE_ALIAS) = ...
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    public_key: constr(min_length=44, max_length=512) = ...

    @validator("public_key")
    def validate_public_key(cls, v):
        return validate_base64(v, "public_key")


class RegisterResponse(BaseModel):
    user_id: str


class ChallengeRequest(BaseModel):
    user_id: constr(regex=RE_USER_ID) = ...


class ChallengeResponse(BaseModel):
    challenge: str


class VerifyRequest(BaseModel):
    user_id: constr(regex=RE_USER_ID) = ...
    signature: str  # base64 de firma sobre el challenge

    @validator("signature")
    def validate_public_key(cls, v):
        return validate_base64(v, "signature")


class VerifyResponse(BaseModel):
    access_token: str

