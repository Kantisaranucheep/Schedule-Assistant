"""Authentication schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)


class LoginResponse(BaseModel):
    """Login response payload."""

    user_id: UUID
    username: str
    name: str
    email: str
    message: str = "Login successful"
