from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SummaryOut(ContractModel):
    active_subscriptions: int = 0
    paused_subscriptions: int = 0
    mrr: Decimal = Decimal("0.00")
    collected: Decimal = Decimal("0.00")
    invoiced: Decimal = Decimal("0.00")
    outstanding: Decimal = Decimal("0.00")
    overdue_count: int = 0


class MonthRevenueOut(ContractModel):
    month: date
    revenue_collected: Decimal
    invoiced: Decimal


class BreakdownOut(ContractModel):
    active: int = 0
    paused: int = 0
    by_plan: dict[str, int] = Field(default_factory=dict)


class OverdueInvoiceOut(ContractModel):
    invoice_id: int
    invoice_number: str
    customer_name: str
    due_date: date
    days_overdue: int
    amount_due: Decimal


class OverdueSummaryOut(ContractModel):
    count: int = 0
    amount_due: Decimal = Decimal("0.00")


class DryRunOut(ContractModel):
    as_of: date
    eligible_count: int = 0


class GenerationFailureOut(ContractModel):
    sub_id: int
    error: str


class GenerateResultOut(ContractModel):
    created: int = 0
    skipped_duplicates: int = 0
    failed: list[GenerationFailureOut] = Field(default_factory=list)


class InvoiceBreakdownLineOut(ContractModel):
    description: str
    quantity: int
    unit_price: Decimal
    variant_extra: Decimal
    discount_name: str | None
    discount_amount: Decimal
    discount_reason: str | None
    tax_name: str | None
    tax_rate_pct: Decimal | None
    tax_amount: Decimal
    line_total: Decimal


class InvoiceBreakdownOut(ContractModel):
    invoice_id: int
    invoice_number: str
    lines: list[InvoiceBreakdownLineOut]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal


class PaymentOut(ContractModel):
    id: int
    invoice_id: int
    amount: Decimal
    paid_on: date
    method: str


class SubscriptionOut(ContractModel):
    id: int
    number: str
    customer_id: int
    plan_id: int
    status: str
    start_date: date
    next_invoice_date: date | None
    is_paused: bool = False


class InvoiceOut(ContractModel):
    id: int
    number: str
    customer_id: int
    status: str
    invoice_date: date
    due_date: date
    total: Decimal
    amount_due: Decimal


class DiscountOut(ContractModel):
    id: int
    name: str
    type: str
    value: Decimal
    scope: str

