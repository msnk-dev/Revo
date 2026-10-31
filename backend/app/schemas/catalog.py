from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from app.schemas.contract import ContractModel

ProductType = Literal["service", "software", "addon", "physical"]
BillingPeriod = Literal["daily", "weekly", "monthly", "yearly"]
DiscountType = Literal["fixed", "percent"]


class CatalogModel(ContractModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProductCreateIn(CatalogModel):
    name: str = Field(min_length=1, max_length=160)
    type: ProductType
    sales_price: Decimal = Field(ge=0, decimal_places=2)
    cost_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    notes: str | None = Field(default=None, max_length=4000)
    default_tax_id: int | None = Field(default=None, gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductOut(CatalogModel):
    id: int
    name: str
    type: ProductType
    sales_price: Decimal
    cost_price: Decimal
    notes: str | None
    default_tax_id: int | None
    is_active: bool


class ProductListOut(CatalogModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int


class VariantValueIn(CatalogModel):
    value: str = Field(min_length=1, max_length=100)
    extra_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)

    @field_validator("value", mode="before")
    @classmethod
    def strip_value(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class VariantAttributeIn(CatalogModel):
    name: str = Field(min_length=1, max_length=100)
    values: list[VariantValueIn] = Field(min_length=1, max_length=50)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class VariantValueOut(CatalogModel):
    id: int
    value: str
    extra_price: Decimal


class VariantAttributeOut(CatalogModel):
    id: int
    product_id: int
    name: str
    values: list[VariantValueOut]


class TaxCreateIn(CatalogModel):
    name: str = Field(min_length=1, max_length=100)
    rate_pct: Decimal = Field(ge=0, le=100, decimal_places=2)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TaxOut(CatalogModel):
    id: int
    name: str
    rate_pct: Decimal
    is_active: bool


class TaxListOut(CatalogModel):
    items: list[TaxOut]
    total: int
    page: int
    page_size: int


class PlanCreateIn(CatalogModel):
    name: str = Field(min_length=1, max_length=160)
    price: Decimal = Field(ge=0, decimal_places=2)
    billing_period: BillingPeriod
    min_quantity: int = Field(default=1, ge=1)
    available_from: date | None = None
    available_to: date | None = None
    auto_close: bool = False
    closable: bool = True
    pausable: bool = True
    renewable: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("available_to")
    @classmethod
    def validate_availability_window(cls, value: date | None, info):
        available_from = info.data.get("available_from")
        if value and available_from and value < available_from:
            raise ValueError("available_to must be on or after available_from")
        return value


class PlanOut(CatalogModel):
    id: int
    name: str
    price: Decimal
    billing_period: BillingPeriod
    min_quantity: int
    available_from: date | None
    available_to: date | None
    auto_close: bool
    closable: bool
    pausable: bool
    renewable: bool
    is_active: bool


class PlanListOut(CatalogModel):
    items: list[PlanOut]
    total: int
    page: int
    page_size: int


class PaymentMethodIn(CatalogModel):
    name: str = Field(min_length=1, max_length=40)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class PaymentMethodOut(CatalogModel):
    id: int
    name: str
    is_active: bool


class PaymentMethodListOut(CatalogModel):
    items: list[PaymentMethodOut]
    total: int
    page: int
    page_size: int


class QuotationTemplateLineIn(CatalogModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100000)
    variant_value_ids: list[int] = Field(default_factory=list, max_length=20)


class QuotationTemplateIn(CatalogModel):
    name: str = Field(min_length=1, max_length=160)
    plan_id: int = Field(gt=0)
    validity_days: int = Field(ge=1, le=365)
    lines: list[QuotationTemplateLineIn] = Field(min_length=1, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class QuotationTemplateLineOut(CatalogModel):
    id: int
    product_id: int
    quantity: int
    variant_value_ids: list[int]


class QuotationTemplateOut(CatalogModel):
    id: int
    name: str
    plan_id: int
    validity_days: int
    lines: list[QuotationTemplateLineOut]


class QuotationTemplateListOut(CatalogModel):
    items: list[QuotationTemplateOut]
    total: int
    page: int
    page_size: int

