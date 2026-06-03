"""
app/services/auth_service.py
─────────────────────────────
Business logic for authentication: registration, login, JWT, GitHub OAuth.

Why this is separate from the router:
- Routers handle HTTP (request parsing, response formatting, status codes)
- Services handle BUSINESS LOGIC (hashing, token creation, validation rules)
- Services are testable without HTTP — you can call them directly in unit tests

JWT design:
- Access token: short-lived (30 min), used for API requests
- Refresh token: long-lived (7 days), used ONLY to get new access tokens
- Token type field inside payload prevents using refresh tokens as access tokens
"""

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.user_repo import UserRepository
from app.schemas.token import Token, TokenPayload
from app.schemas.user import UserCreate

# ── Password hashing ──────────────────────────────────────────────────────────
# bcrypt is the industry standard for password hashing.
# It is intentionally slow (work factor) to make brute-force attacks expensive.
# deprecated="auto" means old hash formats are automatically upgraded on next login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT token creation ────────────────────────────────────────────────────────

def create_access_token(user_id: uuid.UUID) -> str:
    """
    Create a short-lived JWT access token.
    
    The payload contains:
    - sub: the user's UUID (standard JWT claim for subject)
    - type: "access" — prevents refresh tokens from being used as access tokens
    - exp: expiry timestamp — jose validates this automatically
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a long-lived JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.
    Raises JWTError if the token is expired, tampered with, or malformed.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return TokenPayload(sub=payload["sub"], type=payload["type"])


def create_token_pair(user_id: uuid.UUID) -> Token:
    """Create both access + refresh tokens for a user (used on login/register)."""
    return Token(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


# ── Auth service class ────────────────────────────────────────────────────────

class AuthService:
    """Orchestrates authentication business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: UserCreate) -> Token:
        """
        Register a new user with email + password.
        
        Steps:
        1. Check email is not already taken
        2. Hash the password (NEVER store plain text)
        3. Create the user in the DB
        4. Return a token pair (user is immediately logged in after registration)
        """
        if await self.user_repo.email_exists(data.email):
            # Import here to avoid circular imports
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        hashed_pw = hash_password(data.password)
        user = await self.user_repo.create(
            email=data.email,
            hashed_password=hashed_pw,
        )
        return create_token_pair(user.id)

    async def login(self, email: str, password: str) -> Token:
        """
        Authenticate with email + password.
        
        Security note: we return the SAME error for "user not found" and
        "wrong password". This prevents user enumeration attacks — an attacker
        can't tell whether the email exists or not.
        """
        from fastapi import HTTPException, status

        INVALID_CREDENTIALS = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

        user = await self.user_repo.get_by_email(email)
        if not user:
            raise INVALID_CREDENTIALS

        if not user.hashed_password:
            # This is a GitHub OAuth user — they have no password
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account uses GitHub login. Please sign in with GitHub.",
            )

        if not verify_password(password, user.hashed_password):
            raise INVALID_CREDENTIALS

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        return create_token_pair(user.id)

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Exchange a valid refresh token for a new access token.
        Returns only the new access token string.
        """
        from fastapi import HTTPException, status
        from jose import JWTError

        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        if payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is not a refresh token",
            )

        user = await self.user_repo.get_by_id(uuid.UUID(payload.sub))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        return create_access_token(user.id)

    async def get_or_create_github_user(
        self,
        github_id: str,
        email: str,
    ) -> Token:
        """
        Handle GitHub OAuth callback.
        
        Logic:
        1. If we already have a user with this github_id → log them in
        2. Else if we have a user with this email → link their GitHub account
        3. Else → create a brand new account
        """
        # Check if GitHub account already linked
        user = await self.user_repo.get_by_github_id(github_id)
        if user:
            return create_token_pair(user.id)

        # Check if email already registered (link GitHub to existing account)
        user = await self.user_repo.get_by_email(email)
        if user:
            # Link GitHub to existing email account
            user.github_id = github_id
            await self.db.commit()
            return create_token_pair(user.id)

        # Brand new user via GitHub
        user = await self.user_repo.create(
            email=email,
            github_id=github_id,
        )
        return create_token_pair(user.id)
