from dataclasses import dataclass
from datetime import date
from typing import Callable

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import Actor
from app.errors import ForbiddenError, NotFoundError, ValidationFailed
from app.models import Customer, Invoice
from app.services import billing, customers, discounts, email, invoices, reports, subscriptions
from app.ai.schemas import (
    DiscountArgs,
    DryRunArgs,
    EmptyArgs,
    InvoiceArgs,
    MyInvoicesArgs,
    OverdueArgs,
    PaymentHistoryArgs,
    ProposeBillingArgs,
    ProposeReminderArgs,
    RevenueArgs,
    SummaryArgs,
)


@dataclass
class ToolContext:
    db: Session
    actor: Actor
    proposal: dict | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args: type[BaseModel]
    roles: tuple[str, ...]
    handler: Callable[[BaseModel, ToolContext], object]

    def openai_spec(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args.model_json_schema(),
            },
        }


def _json(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


def _summary(args: BaseModel, ctx: ToolContext):
    value = SummaryArgs.model_validate(args)
    return reports.get_summary(ctx.db, value.date_from, value.date_to)


def _revenue(args: BaseModel, ctx: ToolContext):
    value = RevenueArgs.model_validate(args)
    return reports.get_revenue_by_month(ctx.db, value.date_from, value.date_to)


def _breakdown(_args: BaseModel, ctx: ToolContext):
    return reports.get_active_subscriptions_breakdown(ctx.db)


def _overdue(args: BaseModel, ctx: ToolContext):
    value = OverdueArgs.model_validate(args)
    return reports.list_overdue(ctx.db, value.limit)


def _overdue_summary(_args: BaseModel, ctx: ToolContext):
    return reports.get_overdue_summary(ctx.db)


def _dry_run(args: BaseModel, ctx: ToolContext):
    value = DryRunArgs.model_validate(args)
    return billing.dry_run_generate(ctx.db, value.as_of)


def _invoice(args: BaseModel, ctx: ToolContext):
    value = InvoiceArgs.model_validate(args)
    return billing.get_invoice_breakdown(ctx.db, ctx.actor, value.invoice_id)


def _my_subscriptions(_args: BaseModel, ctx: ToolContext):
    if ctx.actor.customer_id is None:
        raise NotFoundError("Customer account not found")
    return subscriptions.list_for_customer(ctx.db, ctx.actor.customer_id)


def _my_invoices(args: BaseModel, ctx: ToolContext):
    if ctx.actor.customer_id is None:
        raise NotFoundError("Customer account not found")
    value = MyInvoicesArgs.model_validate(args)
    return invoices.list_for_customer(ctx.db, ctx.actor.customer_id, value.status)


def _payment_history(args: BaseModel, ctx: ToolContext):
    value = PaymentHistoryArgs.model_validate(args)
    customer_id = ctx.actor.customer_id if ctx.actor.role == "customer" else value.customer_id
    if customer_id is None:
        raise ValidationFailed("customer_id is required for staff payment history", {"customer_id": "Required"})
    if ctx.actor.role == "customer" and value.customer_id not in (None, ctx.actor.customer_id):
        raise NotFoundError("Customer account not found")
    return customers.get_payment_history(ctx.db, customer_id, value.limit)


def _eligible_discounts(args: BaseModel, ctx: ToolContext):
    value = DiscountArgs.model_validate(args)
    customer_id = ctx.actor.customer_id if ctx.actor.role == "customer" else value.customer_id
    if customer_id is None:
        raise ValidationFailed("customer_id is required", {"customer_id": "Required"})
    if ctx.actor.role == "customer" and value.customer_id not in (None, ctx.actor.customer_id):
        raise NotFoundError("Customer account not found")
    return discounts.list_eligible(ctx.db, customer_id, value.quantity, value.product_id)


def _propose_billing(args: BaseModel, ctx: ToolContext):
    value = ProposeBillingArgs.model_validate(args)
    if ctx.actor.role not in {"admin", "staff"}:
        raise ForbiddenError("Only staff can propose a billing run")
    if ctx.proposal is not None:
        raise ValidationFailed("Only one action may be proposed per assistant run")
    preview = billing.dry_run_generate(ctx.db, value.as_of)
    ctx.proposal = {"action": "run_billing", "as_of": value.as_of.isoformat()}
    return {"proposal": "Run the deterministic billing service after a staff member confirms", "preview": _json(preview)}


def _propose_reminder(args: BaseModel, ctx: ToolContext):
    value = ProposeReminderArgs.model_validate(args)
    if ctx.actor.role not in {"admin", "staff"}:
        raise ForbiddenError("Only staff can draft collection reminders")
    if ctx.proposal is not None:
        raise ValidationFailed("Only one action may be proposed per assistant run")
    invoice = ctx.db.get(Invoice, value.invoice_id)
    if invoice is None or invoice.status != "confirmed" or invoice.amount_due <= 0 or invoice.due_date >= date.today():
        raise NotFoundError("Overdue invoice not found")
    customer = ctx.db.get(Customer, invoice.customer_id)
    if customer is None:
        raise NotFoundError("Invoice customer not found")
    ctx.proposal = {
        "action": "send_reminder",
        "invoice_id": invoice.id,
        "subject": value.subject.strip(),
        "body": value.body.strip(),
    }
    return {"proposal": "Draft reminder prepared for staff review", "invoice_number": invoice.number,
            "customer_name": customer.name, "amount_due": str(invoice.amount_due), "body": value.body.strip()}


TOOLS: tuple[Tool, ...] = (
    Tool("get_summary", "Read report totals for an inclusive date range. Use report values; do not calculate money.", SummaryArgs, ("admin", "staff"), _summary),
    Tool("get_revenue_by_month", "Read monthly invoiced and collected totals for an inclusive date range.", RevenueArgs, ("admin", "staff"), _revenue),
    Tool("get_active_subscriptions_breakdown", "Read active and paused subscriptions grouped by plan.", EmptyArgs, ("admin", "staff"), _breakdown),
    Tool("list_overdue_invoices", "List a bounded set of overdue invoices with balances and days overdue.", OverdueArgs, ("admin", "staff"), _overdue),
    Tool("get_overdue_summary", "Read the current overdue invoice count and balance.", EmptyArgs, ("admin", "staff"), _overdue_summary),
    Tool("dry_run_generate_invoices", "Preview the deterministic invoice run without changing data.", DryRunArgs, ("admin", "staff"), _dry_run),
    Tool("get_invoice_breakdown", "Explain a single invoice using its stored line snapshots; customers can only read their own invoice.", InvoiceArgs, ("admin", "staff", "customer"), _invoice),
    Tool("get_my_subscriptions", "List only the signed-in customer's subscriptions.", EmptyArgs, ("customer",), _my_subscriptions),
    Tool("get_my_invoices", "List only the signed-in customer's invoices.", MyInvoicesArgs, ("customer",), _my_invoices),
    Tool("get_customer_payment_history", "Read bounded payment history. Customer callers are scoped to their own account.", PaymentHistoryArgs, ("admin", "staff", "customer"), _payment_history),
    Tool("list_eligible_discounts", "List existing eligible discounts for a customer and quantity; does not create or apply discounts.", DiscountArgs, ("admin", "staff", "customer"), _eligible_discounts),
    Tool("propose_run_billing", "Propose a billing run for human confirmation; never runs billing directly.", ProposeBillingArgs, ("admin", "staff"), _propose_billing),
    Tool("propose_send_reminder", "Draft a reminder for a verified overdue invoice. Sending requires separate human confirmation.", ProposeReminderArgs, ("admin", "staff"), _propose_reminder),
)

TOOL_BY_NAME = {tool.name: tool for tool in TOOLS}


def available_tools(actor: Actor) -> list[Tool]:
    return [tool for tool in TOOLS if actor.role in tool.roles]


def execute_tool(name: str, arguments: object, context: ToolContext):
    tool = TOOL_BY_NAME.get(name)
    if tool is None or context.actor.role not in tool.roles:
        raise ForbiddenError("This assistant tool is unavailable for this account")
    payload = tool.args.model_validate(arguments)
    return _json(tool.handler(payload, context))
