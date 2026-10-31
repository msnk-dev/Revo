from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.contract import ContractModel


class SignupIn(ContractModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=9, max_length=128)
    company: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    role: str | None = Field(default=None, max_length=16)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def enforce_password_rule(cls, value: str) -> str:
        missing = []
        if not any(char.isupper() for char in value):
            missing.append("uppercase letter")
        if not any(char.islower() for char in value):
            missing.append("lowercase letter")
        if not any(not char.isalnum() for char in value):
            missing.append("special character")
        if missing:
            raise ValueError("Password must include a " + ", a ".join(missing))
        return value


class LoginIn(ContractModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class ForgotPasswordIn(ContractModel):
    email: EmailStr = Field(max_length=320)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class ResetPasswordIn(ContractModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=9, max_length=128)

    @field_validator("new_password")
    @classmethod
    def enforce_password_rule(cls, value: str) -> str:
        return SignupIn.enforce_password_rule(value)


class StaffCreateIn(ContractModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=9, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def enforce_password_rule(cls, value: str) -> str:
        return SignupIn.enforce_password_rule(value)


class StaffDeactivateIn(ContractModel):
    is_active: Literal[False] = False


class AuthOut(ContractModel):
    user_id: int
    email: EmailStr
    role: Literal["admin", "staff", "customer"]
    customer_id: int | None


class StaffOut(ContractModel):
    id: int
    name: str | None
    email: EmailStr
    role: Literal["admin", "staff", "customer"]
    is_active: bool


class StaffListOut(ContractModel):
    items: list[StaffOut]
    total: int
    page: int
    page_size: int

