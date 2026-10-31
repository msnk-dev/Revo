from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatIn(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = Field(default=None, max_length=80)


class RouteOut(StrictModel):
    agent: Literal["revenue_insights", "invoice_explainer", "collections", "billing_ops", "discount_advisor"]
    intent: Literal[
        "revenue_summary", "invoice_explanation", "compare_previous_invoice", "collections",
        "billing_preview", "discount_simulation", "propose_discount_rule", "account_help", "general_question",
    ]


class AIRunOut(StrictModel):
    id: int
    agent: str
    user_id: int | None
    status: str
    provider: str | None
    model: str | None
    created_at: str


class AIRunListOut(StrictModel):
    items: list[AIRunOut]
    total: int
    page: int
    page_size: int


class FailedRunExplanationOut(StrictModel):
    id: int
    status: str
    explanation: str
    provider: str | None


class RouteIn(StrictModel):
    message: str = Field(min_length=1, max_length=2000)


class ProposalOut(StrictModel):
    id: str
    action: Literal["run_billing", "send_reminder", "create_discount_rule"]
    title: str
    description: str
    subject: str | None = None
    body: str | None = None


class ChatOut(StrictModel):
    answer: str
    thread_id: str
    proposals: list[ProposalOut] = Field(default_factory=list)
    provider: str | None = None
    offline: bool = False


class ActionOut(StrictModel):
    id: int
    status: Literal["confirmed", "rejected", "sent"]
    result: dict = Field(default_factory=dict)


class EmptyArgs(StrictModel):
    pass


class SummaryArgs(StrictModel):
    date_from: date
    date_to: date


class RevenueArgs(StrictModel):
    date_from: date
    date_to: date


class OverdueArgs(StrictModel):
    limit: int = Field(default=20, ge=1, le=50)


class DryRunArgs(StrictModel):
    as_of: date = Field(default_factory=date.today)


class InvoiceArgs(StrictModel):
    invoice_id: int = Field(gt=0)


class DiscountSimulationArgs(StrictModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100000)
    discount_id: int | None = Field(default=None, gt=0)
    as_of: date = Field(default_factory=date.today)


class CompareInvoiceArgs(StrictModel):
    invoice_id: int = Field(gt=0)


class MyInvoicesArgs(StrictModel):
    status: str | None = Field(default=None, pattern="^(draft|confirmed|paid|cancelled)$")


class PaymentHistoryArgs(StrictModel):
    customer_id: int | None = Field(default=None, gt=0)
    limit: int = Field(default=20, ge=1, le=50)


class DiscountArgs(StrictModel):
    customer_id: int | None = Field(default=None, gt=0)
    quantity: int = Field(ge=1, le=100000)
    product_id: int | None = Field(default=None, gt=0)


class ProposeBillingArgs(StrictModel):
    as_of: date = Field(default_factory=date.today)


class ProposeReminderArgs(StrictModel):
    invoice_id: int = Field(gt=0)
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)


class ToolArgs(StrictModel):
    pass


class DateRangeArgs(ToolArgs):
    date_from: date = Field(alias="from")
    date_to: date = Field(alias="to")


class LimitArgs(ToolArgs):
    limit: int = Field(default=20, ge=1, le=50)


class ReminderProposalArgs(ToolArgs):
    invoice_id: int = Field(gt=0)
    recipient_email: EmailStr
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)


class RouteDecision(StrictModel):
    agent: str | None
    intent: str = Field(max_length=120)
