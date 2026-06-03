"""
app/schemas/user.py
───────────────────
Pydantic v2 schemas for User — request validation and response shaping.

Key pattern: NEVER return the hashed_password in any response.
We have three schemas:
- UserCreate: what we receive from the client (email + password)
- UserResponse: what we send back (no password, no sensitive fields)
- UserUpdate: for future profile update endpoint
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    """Request body for POST /api/v1/auth/register"""
    email: EmailStr                         # Validates real email format (e.g. rejects "notanemail")
    password: str = Field(min_length=8)    # Enforce minimum password length at schema level

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "securepassword123"
                }
            ]
        }
    }


class UserLogin(BaseModel):
    """Request body for POST /api/v1/auth/login"""
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "securepassword123"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """
    Response shape for any endpoint that returns a user.
    Notice: no hashed_password field — we NEVER expose this.
    
    model_config with from_attributes=True allows Pydantic to read
    from SQLAlchemy ORM objects directly (not just dicts).
    """
    id: uuid.UUID
    email: str
    github_id: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Allows: UserResponse.model_validate(orm_object)
