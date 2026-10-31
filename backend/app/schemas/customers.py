from pydantic import EmailStr, Field, field_validator

from app.schemas.catalog import CatalogModel


class CustomerCreateIn(CatalogModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr = Field(max_length=320)
    phone: str | None = Field(default=None, max_length=40)
    company: str | None = Field(default=None, max_length=160)
    billing_address: str | None = Field(default=None, max_length=4000)
    tax_id: str | None = Field(default=None, max_length=80)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class CustomerOut(CatalogModel):
    id: int
    user_id: int | None
    name: str
    email: str
    phone: str | None
    company: str | None
    billing_address: str | None
    tax_id: str | None
    is_active: bool


class CustomerListOut(CatalogModel):
    items: list[CustomerOut]
    total: int
    page: int
    page_size: int
