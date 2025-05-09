# files.py

from fastapi import APIRouter, HTTPException, status, Depends
from core.auth import require_auth


# instancia de enrutador modular
router = APIRouter()


@router.get("/files")
async def list_files(user_id: str = Depends(require_auth)):
    return {
        "status": "ok",
        "message": f"Access granted for user {user_id}",
        "files": []  # Aquí luego pondrás los ficheros reales
    }

