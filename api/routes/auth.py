# api/routes/auth.py

from fastapi import APIRouter, HTTPException, status
from api.models.auth import ChallengeRequest, ChallengeResponse, RegisterRequest, RegisterResponse, VerifyRequest, VerifyResponse
from core.auth import generate_challenge, get_challenge, create_session_token, verify_session_token
from core.users import register as register_user, exists as user_exists, get_public_key as get_user_public_key
from core.events import build_user_registered_event, publish_event
from utils.crypto import verify_signature


# instancia de enrutador modular
router = APIRouter()


@router.post("/challenge", response_model=ChallengeResponse)
async def request_challenge(payload: ChallengeRequest):
    # Para iniciar el proceso, el usuario debe existir
    if not user_exists(payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")

    # Generamos un challenge asociado al user y lo guardamos en cache
    challenge = generate_challenge(payload.user_id)

    return ChallengeResponse(challenge=challenge)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    # Verificamos que el usuario no exista
    if user_exists(payload.user_id):
        raise HTTPException(status_code=409, detail="User already exists")

    # Construimos el evento y enviamos a iota / mqtt
    event = build_user_registered_event(payload.dict())
    block_id = publish_event(event)

    return RegisterResponse(user_id=payload.user_id)


@router.post("/verify", response_model=VerifyResponse)
async def verify(payload: VerifyRequest):
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
    token = create_session_token(payload.user_id)

    return VerifyResponse(access_token=token)

