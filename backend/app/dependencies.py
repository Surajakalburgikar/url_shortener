"""
app/dependencies.py
────────────────────
Reusable FastAPI dependency functions — injected into routes via Depends().

Why dependencies?
- Instead of repeating "get the current user from the JWT" in every protected route,
  we define it once here and inject it with:  user = Depends(get_current_user)
- FastAPI resolves the dependency chain automatically.
- Dependencies are also easy to override in tests (swap with a fake user).

Dependency chain for a protected endpoint:
  Request → Authorization header → decode JWT → get user from DB → inject into endpoint
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import decode_token

# HTTPBearer extracts the token from "Authorization: Bearer <token>" header
# auto_error=False means it returns None instead of raising 403 if header is missing
# This lets us handle the error ourselves with a better message
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency for protected endpoints.
    
    Extracts JWT from Authorization header, validates it, and returns the User object.
    Raises 401 if token is missing, expired, or invalid.
    
    Usage:
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated — provide a Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provide an access token, not a refresh token",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(payload.sub))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Dependency for endpoints that work for BOTH anonymous and authenticated users.
    
    - Anonymous users (no token): returns None
    - Authenticated users (valid token): returns the User object
    - Invalid token: raises 401
    
    Used by: POST /api/v1/links (anonymous can create links, logged-in users get ownership)
    """
    if not credentials:
        return None  # Anonymous — that's fine

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.type != "access":
        return None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(payload.sub))
    return user if (user and user.is_active) else None
