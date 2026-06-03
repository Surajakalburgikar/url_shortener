"""
app/models/__init__.py
──────────────────────
Re-exports all ORM models from one place.

Why this matters:
- Alembic's env.py imports Base from app.database.
- For Alembic to detect all tables, every model class MUST be imported
  somewhere before Alembic reads Base.metadata.
- Importing them all here, then importing this module in env.py,
  guarantees all tables are registered with SQLAlchemy's metadata.
"""

from app.models.click import Click
from app.models.link import Link
from app.models.user import User

__all__ = ["User", "Link", "Click"]
