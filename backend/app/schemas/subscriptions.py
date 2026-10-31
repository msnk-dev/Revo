from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.catalog import CatalogModel


class SubscriptionLineIn(CatalogModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100000)
    variant_value_ids: list[int] = Field(default_factory=list, max_length=20)
    description: str | None = Field(default=None, max_length=240)


class SubscriptionCreateIn(CatalogModel):
    customer_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    start_date: date
    expiry_date: date | None = None
    payment_terms_days: int = Field(default=0, ge=0, le=365)
    lines: list[SubscriptionLineIn] = Field(min_length=1, max_length=100)


class SubscriptionFromTemplateIn(CatalogModel):
    customer_id: int = Field(gt=0)
    start_date: date


class SubscriptionUpdateIn(CatalogModel):
    start_date: date | None = None
    expiry_date: date | None = None
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    lines: list[SubscriptionLineIn] | None = Field(default=None, min_length=1, max_length=100)


class SubscriptionTransitionIn(CatalogModel):
    to: str = Field(pattern="^(quotation|confirmed|active)$")


class SubscriptionLineOut(CatalogModel):
    id: int
    product_id: int
    description: str
    quantity: int
    unit_price: Decimal
    tax_id: int | None
    variant_value_ids: list[int]


class SubscriptionHistoryOut(CatalogModel):
    id: int
    from_status: str | None
    to_status: str
    changed_by: int | None
    changed_at: datetime


class SubscriptionDetailOut(CatalogModel):
    id: int
    number: str
    customer_id: int
    plan_id: int
    status: str
    start_date: date
    expiry_date: date | None
    next_invoice_date: date | None
    payment_terms_days: int
    quotation_expires_on: date | None
    is_paused: bool
    paused_at: datetime | None
    closed_at: datetime | None
    lines: list[SubscriptionLineOut]
    history: list[SubscriptionHistoryOut]


class SubscriptionListOut(CatalogModel):
    items: list[SubscriptionDetailOut]
    total: int
    page: int
    page_size: int


class SubscriptionRenewalOut(CatalogModel):
    subscription: SubscriptionDetailOut
