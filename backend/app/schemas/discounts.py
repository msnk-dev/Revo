from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.catalog import CatalogModel


class DiscountCreateIn(CatalogModel):
    name: str = Field(min_length=1, max_length=160)
    type: Literal["fixed", "percent"]
    value: Decimal = Field(gt=0, decimal_places=2)
    scope: Literal["product", "subscription"]
    min_purchase: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    min_quantity: int = Field(default=1, ge=1)
    start_date: date | None = None
    end_date: date | None = None
    max_uses: int | None = Field(default=None, ge=1)
    product_ids: list[int] = Field(default_factory=list, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_discount(self):
        if self.type == "percent" and self.value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.scope == "product" and not self.product_ids:
            raise ValueError("product discounts need at least one product")
        if self.scope == "subscription" and self.product_ids:
            raise ValueError("subscription discounts cannot specify products")
        if len(self.product_ids) != len(set(self.product_ids)) or any(item <= 0 for item in self.product_ids):
            raise ValueError("product_ids must be unique positive IDs")
        return self


class DiscountDetailOut(CatalogModel):
    id: int
    name: str
    type: Literal["fixed", "percent"]
    value: Decimal
    scope: Literal["product", "subscription"]
    min_purchase: Decimal
    min_quantity: int
    start_date: date | None
    end_date: date | None
    max_uses: int | None
    uses_count: int
    is_active: bool
    product_ids: list[int]


class DiscountListOut(CatalogModel):
    items: list[DiscountDetailOut]
    total: int
    page: int
    page_size: int
