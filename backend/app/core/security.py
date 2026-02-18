import threading

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import DecodeError, ExpiredSignatureError, PyJWKClient, PyJWTError
from jwt import decode as jwt_decode
from jwt import get_unverified_header

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
security_scheme = HTTPBearer()

# Cache the JWKS client per Supabase project (thread-safe singleton)
_jwks_client: PyJWKClient | None = None
_jwks_lock = threading.Lock()


def _get_jwks_client() -> PyJWKClient:
    """Get or create a cached JWKS client for Supabase."""
    global _jwks_client
    if _jwks_client is None:
        with _jwks_lock:
            if _jwks_client is None:
                settings = get_settings()
                jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
                _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def decode_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT token.

    Supports both asymmetric (ES256, RS256) and symmetric (HS256) algorithms.
    Supabase projects with new JWT Signing Keys use ES256.
    """
    settings = get_settings()

    # Peek at the token header to determine the algorithm
    try:
        header = get_unverified_header(token)
        alg = header.get("alg", "HS256")
    except DecodeError:
        alg = "HS256"

    # Asymmetric algorithms (ES256, RS256, etc.) → use JWKS public key
    if alg.startswith("ES") or alg.startswith("RS") or alg.startswith("PS"):
        return _decode_with_jwks(token, alg)

    # Symmetric HMAC algorithms (HS256, HS384, HS512) → use JWT secret
    return _decode_with_secret(token, alg, settings.supabase_jwt_secret)


def _decode_with_jwks(token: str, alg: str) -> dict:
    """Decode JWT using JWKS public key (for ES256/RS256)."""
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt_decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience="authenticated",
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWTError as e:
        # Retry without audience check
        try:
            client = _get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            return jwt_decode(
                token,
                signing_key.key,
                algorithms=[alg],
                options={"verify_aud": False},
            )
        except PyJWTError as e2:
            logger.warning("jwt_verification_failed: alg=%s, error=%s", alg, str(e2))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )


def _decode_with_secret(token: str, alg: str, secret: str) -> dict:
    """Decode JWT using HMAC symmetric secret (for HS256/HS384/HS512)."""
    allowed_algs = [alg] if alg.startswith("HS") else ["HS256"]

    # Try with audience verification first
    try:
        return jwt_decode(
            token, secret, algorithms=allowed_algs, audience="authenticated",
        )
    except PyJWTError:
        pass

    # Fallback: without audience check
    try:
        return jwt_decode(
            token, secret, algorithms=allowed_algs, options={"verify_aud": False},
        )
    except PyJWTError as e:
        logger.warning("jwt_verification_failed: alg=%s, error=%s", alg, str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """Extract and validate the current user from JWT."""
    payload = decode_jwt(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role", "authenticated"),
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role for the endpoint."""
    app_metadata = current_user.get("app_metadata", {})
    role = current_user.get("role", "")

    is_admin = role == "service_role" or app_metadata.get("role") == "admin"

    if not is_admin:
        logger.warning("unauthorized_admin_access: user_id=%s", current_user["id"])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
