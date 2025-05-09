# validators.py

import base64


def validate_base64(value: str, field_name: str) -> str:
    try:
        base64.b64decode(value, validate=True)
    except Exception:
        raise ValueError(f"{field_name} must be a valid base64-encoded string")
    return value

