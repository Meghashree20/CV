"""Security utilities: password hashing and JWT handling.

Implemented without external dependencies to work in the offline sandbox.
Uses PBKDF2-HMAC-SHA256 for password hashing and a minimal HS256 JWT
implementation provided by the local ``jose`` stub package.
"""

import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password with a random 16‑byte salt using PBKDF2-HMAC-SHA256.

    Returns a base64‑encoded string containing ``salt + dk`` where ``dk`` is the
    derived key (32 bytes). The format is compatible with custom verification
    logic in ``verify_password``.
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.b64encode(salt + dk).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against the stored PBKDF2 hash.

    ``hashed_password`` must be the base64 string produced by ``hash_password``.
    """
    try:
        data = base64.b64decode(hashed_password.encode())
        salt, stored_dk = data[:16], data[16:]
        new_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, 100_000)
        return hmac.compare_digest(stored_dk, new_dk)
    except Exception:
        return False

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _jwt_settings() -> Dict[str, Any]:
    """Fetch JWT configuration from settings.

    Raises ``RuntimeError`` if the secret key is missing – test fixtures ensure it
    is set via environment variables.
    """
    settings = get_settings()
    return {
        "secret_key": settings.jwt_secret_key,
        "algorithm": settings.jwt_algorithm,
        "expire_seconds": settings.jwt_expiration_seconds,
    }


def create_access_token(subject: str) -> str:
    """Create a JWT access token for the given subject."""
    cfg = _jwt_settings()

    expire = datetime.now(timezone.utc) + timedelta(
        seconds=cfg["expire_seconds"]
    )

    payload = {
        "sub": subject,
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(
        payload,
        cfg["secret_key"],
        algorithm=cfg["algorithm"],
    )
    
def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token and return its payload.

    ``JWTError`` is raised for invalid signatures or expired tokens.
    """
    cfg = _jwt_settings()
    return jwt.decode(token, cfg["secret_key"], algorithms=[cfg["algorithm"]])
