from enum import Enum
from pydantic import BaseModel, EmailStr


class Role(str, Enum):
    PUBLIC = "public"
    OFFICER = "officer"
    SENIOR_OFFICER = "senior_officer"
    ADMIN = "admin"


class User(BaseModel):
    id: str
    email: EmailStr
    role: Role
    full_name: str | None = None
    officer_id: str | None = None  # KSP-issued, required for officer/senior_officer


class TokenPayload(BaseModel):
    sub: str  # user id
    role: Role
    exp: int
