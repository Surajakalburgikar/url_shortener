"""
app/schemas/token.py
────────────────────
Pydantic v2 schemas for JWT token responses.

Why separate token schemas?
- The login endpoint returns BOTH an access token and a refresh token.
- The refresh endpoint only returns a new access token.
- Having explicit schemas makes this clear in Swagger docs.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """Returned on successful login or registration."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    """Returned on token refresh — only a new access token, not a new refresh token."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    The decoded payload inside a JWT.
    sub = subject = the user's UUID (stored as a string in the JWT).
    """
    sub: str
    type: str  # "access" or "refresh" — prevents using a refresh token as an access token


class RefreshTokenRequest(BaseModel):
    """Request body for POST /api/v1/auth/refresh"""
    refresh_token: str

