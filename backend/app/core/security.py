from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
security_scheme = HTTPBearer()


def decode_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT token."""
    settings = get_settings()
    secret = settings.supabase_jwt_secret

    # Peek at the token header to determine the algorithm
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
    except JWTError:
        alg = "HS256"

    # Supabase may use HS256, HS384, or HS512 depending on project config
    allowed_algs = [alg] if alg.startswith("HS") else ["HS256", "HS384", "HS512"]

    # Try with audience verification first
    try:
        return jwt.decode(
            token, secret, algorithms=allowed_algs, audience="authenticated",
        )
    except JWTError:
        pass

    # Fallback: without audience check (some Supabase configs vary)
    try:
        return jwt.decode(
            token, secret, algorithms=allowed_algs, options={"verify_aud": False},
        )
    except JWTError as e:
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

    # Supabase stores custom roles in app_metadata or user_metadata
    is_admin = role == "service_role" or app_metadata.get("role") == "admin"

    if not is_admin:
        logger.warning("unauthorized_admin_access: user_id=%s", current_user["id"])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
