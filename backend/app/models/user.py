"""
app/models/user.py
──────────────────
User ORM model — maps to the `users` table in PostgreSQL.

Design decisions:
- UUID primary key: can't be guessed or enumerated (security best practice)
- hashed_password is nullable: GitHub OAuth users have no password
- github_id is nullable: email/password users don't have a GitHub ID
- is_active flag: lets us disable accounts without deleting them
- created_at / updated_at: standard audit columns (every production table has these)
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────────────────
    # server_default: PostgreSQL generates the UUID, not Python.
    # This is more reliable in async environments.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    # index=True: makes WHERE email = '...' queries fast (used on every login)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Nullable — OAuth users sign in via GitHub, they have no password
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Nullable — email/password users don't have a GitHub ID
    # unique=True: prevents the same GitHub account linking to multiple users
    github_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Audit timestamps ──────────────────────────────────────────────────────
    # server_default: DB sets this, not Python — survives timezone issues
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # lazy="dynamic" replaced by selectin in SQLAlchemy 2.0 — we'll use explicit joins
    links: Mapped[list["Link"]] = relationship(  # noqa: F821
        "Link",
        back_populates="user",
        cascade="all, delete-orphan",  # Deleting a user deletes all their links
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
