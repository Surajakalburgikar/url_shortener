"""
app/repositories/user_repo.py
──────────────────────────────
Data Access Layer for the User entity.

Every database query related to users lives here — nowhere else.
The service layer calls these methods and never writes raw SQL itself.
This is the Repository pattern.

All methods are async because we use SQLAlchemy 2.0 async.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """All database operations for the User table."""

    def __init__(self, db: AsyncSession) -> None:
        # The session is injected — the repository doesn't create its own sessions.
        # This makes it testable: in tests we pass a test session.
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a user by their UUID primary key."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Fetch a user by email — used on every login attempt.
        Uses the ix_users_email index (O(log n) lookup).
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_github_id(self, github_id: str) -> User | None:
        """Fetch a user by their GitHub numeric ID — used in OAuth flow."""
        result = await self.db.execute(
            select(User).where(User.github_id == github_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: str | None = None,
        github_id: str | None = None,
    ) -> User:
        """
        Create a new user.
        - Email/password users: provide email + hashed_password
        - GitHub OAuth users: provide email + github_id (no password)
        """
        user = User(
            email=email,
            hashed_password=hashed_password,
            github_id=github_id,
        )
        self.db.add(user)
        await self.db.flush()   # Flush to DB (gets the generated UUID) but don't commit yet.
                                # The router's get_db() dependency commits after the endpoint returns.
        await self.db.refresh(user)  # Reload from DB to get server-generated defaults
        return user

    async def email_exists(self, email: str) -> bool:
        """Quick check if an email is already registered — used before creating a user."""
        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None
