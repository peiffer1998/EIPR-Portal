"""Authentication schemas."""
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Response body for access tokens."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str
