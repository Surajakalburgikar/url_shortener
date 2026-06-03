"""
app/models/link.py
──────────────────
Link ORM model — maps to the `links` table in PostgreSQL.

Design decisions:
- short_code has a UNIQUE index: this is the most critical index in the whole project.
  Every redirect does a WHERE short_code = '...' lookup. Without an index,
  PostgreSQL scans every row. With it, lookup is O(log n) — essentially instant.
- user_id is nullable: anonymous users can create short links without an account.
- expires_at is nullable: links are permanent unless expiry is explicitly set.
- Composite index on (user_id, created_at): the dashboard query that lists
  "my links sorted by newest first" uses both columns — the composite index
  covers this exact query pattern.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Link(Base):
    __tablename__ = "links"

    # ── Table-level indexes (composite indexes must be defined here) ──────────
    __table_args__ = (
        # Covers: SELECT * FROM links WHERE user_id = ? ORDER BY created_at DESC
        # Used by the dashboard to list a user's links sorted by newest first.
        Index("ix_links_user_id_created_at", "user_id", "created_at"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── The short code ────────────────────────────────────────────────────────
    # THE most critical column in the project — every redirect hits this.
    # unique=True automatically creates a UNIQUE index (also enforces uniqueness at DB level)
    short_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    # ── The original URL ──────────────────────────────────────────────────────
    # Text (not String) — URLs can be very long (query params, tracking codes, etc.)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Foreign key to User ───────────────────────────────────────────────────
    # nullable=True: anonymous users can create links (no account required)
    # ondelete="SET NULL": if the user is deleted, keep the link but set user_id to NULL
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Expiry ────────────────────────────────────────────────────────────────
    # nullable=True: links are permanent by default
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="links")  # noqa: F821

    clicks: Mapped[list["Click"]] = relationship(  # noqa: F821
        "Click",
        back_populates="link",
        cascade="all, delete-orphan",  # Deleting a link deletes all its clicks
    )

    def __repr__(self) -> str:
        return f"<Link short_code={self.short_code} url={self.original_url[:30]}>"
