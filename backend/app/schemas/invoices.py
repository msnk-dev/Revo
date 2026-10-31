from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.catalog import CatalogModel
from app.schemas.contract import InvoiceOut


class InvoiceListOut(CatalogModel):
    items: list[InvoiceOut]
    total: int
    page: int
    page_size: int


class InvoiceGenerateOut(CatalogModel):
    dry_run: bool
    as_of: date
    eligible_count: int | None = None
    created: int | None = None
    skipped_duplicates: int | None = None
    failed: list[dict] = Field(default_factory=list)


class PaymentCreateIn(CatalogModel):
    method_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, decimal_places=2)
    paid_on: date
    note: str | None = Field(default=None, max_length=500)


class PaymentListOut(CatalogModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


class PaymentReportRowOut(CatalogModel):
    id: int
    invoice_id: int
    invoice_number: str
    customer_name: str
    amount: Decimal
    paid_on: date
    method: str


class PaymentReportOut(CatalogModel):
    items: list[PaymentReportRowOut]
    total: int
    amount: Decimal
    page: int
    page_size: int
