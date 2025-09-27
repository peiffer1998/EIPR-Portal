"""Role helper for explicit authorization checks."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.models.user import User, UserRole


def require_roles(user: User, allowed: set[UserRole]) -> None:
    """Raise HTTP 403 if a user is not a member of the allowed role set."""

    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


__all__ = ["require_roles"]
