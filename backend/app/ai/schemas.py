from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatIn(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = Field(default=None, max_length=80)


class ProposalOut(StrictModel):
    id: str
    action: Literal["run_billing", "send_reminder"]
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
