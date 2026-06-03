"""
app/models/click.py
───────────────────
Click ORM model — maps to the `clicks` table in PostgreSQL.
Records every redirect event for analytics.

Design decisions:
- Composite index on (link_id, clicked_at): the analytics query
  "give me all clicks for link X grouped by day" uses both columns.
  The composite index lets PostgreSQL satisfy this with an index-only scan.
- country, referrer, user_agent are all nullable: we do best-effort geo/referrer
  detection — a missing header should never cause a click to fail to record.
- Clicks are written via a FastAPI BackgroundTask (non-blocking). The redirect
  returns the 307 response immediately; the click is recorded after the response
  is sent. This keeps redirect latency as low as possible.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Click(Base):
    __tablename__ = "clicks"

    # ── Table-level composite index ───────────────────────────────────────────
    __table_args__ = (
        # Covers: SELECT * FROM clicks WHERE link_id = ? ORDER BY clicked_at
        # Used by analytics endpoint — "clicks per day for this link"
        Index("ix_clicks_link_id_clicked_at", "link_id", "clicked_at"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Foreign key to Link ───────────────────────────────────────────────────
    # ondelete="CASCADE": when a Link is deleted, all its clicks are deleted too.
    # This is also handled at the ORM level via cascade="all, delete-orphan" on Link.
    link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("links.id", ondelete="CASCADE"),
        nullable=False,
        index=True,   # Single-column index for quick "all clicks for link X" lookups
    )

    # ── When the click happened ───────────────────────────────────────────────
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Where the click came from ─────────────────────────────────────────────
    # All nullable — we do best-effort detection, never fail on missing headers.

    # 2-letter ISO country code (e.g. "IN", "US") — derived from IP via geo lookup
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # The Referer HTTP header — tells us where the user came from (e.g. "twitter.com")
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # User-Agent header — browser/device info
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # IP address — stored for geo lookup, never exposed in API responses
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # ── Relationship ──────────────────────────────────────────────────────────
    link: Mapped["Link"] = relationship("Link", back_populates="clicks")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Click link_id={self.link_id} at={self.clicked_at}>"
