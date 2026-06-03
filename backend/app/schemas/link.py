"""
app/schemas/link.py
───────────────────
Pydantic v2 schemas for Link — URL creation and response shapes.

Key validation:
- original_url must be a real http/https URL (AnyHttpUrl blocks javascript: and ftp:)
- custom_alias limited to alphanumeric + hyphens (no special chars)
- expires_at must be in the future if provided
- We additionally block localhost URLs in the service layer
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


class LinkCreate(BaseModel):
    """Request body for POST /api/v1/links"""

    # AnyHttpUrl automatically:
    # - Requires http:// or https:// scheme (blocks javascript:, ftp:, etc.)
    # - Validates the URL is structurally valid
    original_url: AnyHttpUrl

    # Optional custom alias — e.g. "my-blog" becomes short.ly/my-blog
    # None means auto-generate a random 6-character code
    custom_alias: str | None = Field(
        default=None,
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9\-]+$",  # Only alphanumeric and hyphens
    )

    # Optional expiry — must be in the future
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def expiry_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            # Make timezone-aware if naive
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("expires_at must be a future datetime")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "original_url": "https://www.example.com/very/long/url",
                    "custom_alias": "my-link",
                    "expires_at": None
                }
            ]
        }
    }


class LinkResponse(BaseModel):
    """Response shape when a link is created or listed."""
    id: uuid.UUID
    short_code: str
    original_url: str
    user_id: uuid.UUID | None = None
    expires_at: datetime | None = None
    created_at: datetime
    click_count: int = 0          # Populated by the service layer from a JOIN or subquery

    model_config = {"from_attributes": True}


class LinkListResponse(BaseModel):
    """Paginated list of links."""
    items: list[LinkResponse]
    total: int
    page: int
    page_size: int
