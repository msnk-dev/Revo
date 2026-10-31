from dataclasses import dataclass
from datetime import date
import json
import logging
import re
from typing import Any, Callable

from pydantic import BaseModel, ValidationError
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
    DateRangeArgs,
    LimitArgs,
    ReminderProposalArgs,
    ToolArgs,
)

logger = logging.getLogger(__name__)
EMAIL_PATTERN = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Z]{2,}(?![\w.-])")


@dataclass
class ToolContext:
    db: Session
    actor: Actor
    proposal: dict | None = None
    user_message: str = ""


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


def execute_tool(name: str, arguments: object, context: ToolContext, agent: str | None = None):
    if agent is not None:
        return _execute_agent_tool(name, arguments, context, agent)
    tool = TOOL_BY_NAME.get(name)
    if tool is None or context.actor.role not in tool.roles:
        raise ForbiddenError("This assistant tool is unavailable for this account")
    payload = tool.args.model_validate(arguments)
    return _json(tool.handler(payload, context))


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[ToolArgs]
    roles: frozenset[str]
    handler: Callable[[ToolContext, ToolArgs], Any]

    def openai_schema(self) -> dict[str, Any]:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.args_model.model_json_schema()}}


STAFF = frozenset({"admin", "staff"})
ALL = frozenset({"admin", "staff", "customer"})


def _agent_summary(context: ToolContext, args: ToolArgs) -> Any:
    params = DateRangeArgs.model_validate(args)
    return reports.get_summary(context.db, params.date_from, params.date_to)


def _agent_revenue_by_month(context: ToolContext, args: ToolArgs) -> Any:
    params = DateRangeArgs.model_validate(args)
    return reports.get_revenue_by_month(context.db, params.date_from, params.date_to)[:50]


def _agent_breakdown(context: ToolContext, args: ToolArgs) -> Any:
    return reports.get_active_subscriptions_breakdown(context.db)


def _agent_overdue_summary(context: ToolContext, args: ToolArgs) -> Any:
    return reports.get_overdue_summary(context.db)


def _agent_list_overdue(context: ToolContext, args: ToolArgs) -> Any:
    params = LimitArgs.model_validate(args)
    return reports.list_overdue(context.db, limit=min(params.limit, 50))


def _agent_payment_history(context: ToolContext, args: ToolArgs) -> Any:
    params = PaymentHistoryArgs.model_validate(args)
    if params.customer_id is None:
        raise ValidationFailed("A customer ID is required")
    if context.actor.role == "customer" and params.customer_id != context.actor.customer_id:
        raise NotFoundError("Customer not found")
    return customers.get_payment_history(context.db, params.customer_id, limit=min(params.limit, 50))


def _agent_invoice_breakdown(context: ToolContext, args: ToolArgs) -> Any:
    params = InvoiceArgs.model_validate(args)
    return billing.get_invoice_breakdown(context.db, context.actor, params.invoice_id)


def _agent_reminder_proposal(context: ToolContext, args: ToolArgs) -> dict[str, Any]:
    params = ReminderProposalArgs.model_validate(args)
    if params.recipient_email.casefold() not in {value.casefold() for value in EMAIL_PATTERN.findall(context.user_message)}:
        raise ValidationFailed("The reminder recipient must be provided explicitly by the staff member")
    overdue = reports.list_overdue(context.db, limit=50)
    invoice = next((item for item in overdue if item.invoice_id == params.invoice_id), None)
    if invoice is None:
        raise NotFoundError("Overdue invoice not found")
    return {"kind": "send_reminder", "invoice_id": invoice.invoice_id, "invoice_number": invoice.invoice_number,
            "customer_name": invoice.customer_name, "recipient_email": str(params.recipient_email),
            "subject": params.subject, "body": params.body}


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "get_summary": ToolDefinition("get_summary", "Get deterministic subscription and revenue summary for a date range.", DateRangeArgs, STAFF, _agent_summary),
    "get_revenue_by_month": ToolDefinition("get_revenue_by_month", "Get collected and invoiced totals by month for a date range.", DateRangeArgs, STAFF, _agent_revenue_by_month),
    "get_active_subscriptions_breakdown": ToolDefinition("get_active_subscriptions_breakdown", "Get active and paused subscription counts grouped by plan.", EmptyArgs, STAFF, _agent_breakdown),
    "get_overdue_summary": ToolDefinition("get_overdue_summary", "Get deterministic count and amount for overdue invoices.", EmptyArgs, STAFF, _agent_overdue_summary),
    "list_overdue_invoices": ToolDefinition("list_overdue_invoices", "List at most 50 overdue invoices.", LimitArgs, STAFF, _agent_list_overdue),
    "get_customer_payment_history": ToolDefinition("get_customer_payment_history", "Get bounded payment history for one customer.", PaymentHistoryArgs, STAFF, _agent_payment_history),
    "get_invoice_breakdown": ToolDefinition("get_invoice_breakdown", "Get the authorized deterministic invoice line breakdown.", InvoiceArgs, ALL, _agent_invoice_breakdown),
    "propose_send_reminder": ToolDefinition("propose_send_reminder", "Create a reminder email draft proposal; this tool never sends email.", ReminderProposalArgs, STAFF, _agent_reminder_proposal),
}

AGENT_TOOLS: dict[str, tuple[str, ...]] = {
    "revenue_insights": ("get_summary", "get_revenue_by_month", "get_active_subscriptions_breakdown", "get_overdue_summary"),
    "invoice_explainer": ("get_invoice_breakdown",),
    "collections": ("list_overdue_invoices", "get_customer_payment_history", "propose_send_reminder"),
}


def schemas_for_agent(agent: str) -> list[dict[str, Any]]:
    return [TOOL_REGISTRY[name].openai_schema() for name in AGENT_TOOLS[agent]]


def _execute_agent_tool(name: str, raw_arguments: object, context: ToolContext, agent: str) -> tuple[Any, dict[str, Any] | None]:
    if name not in AGENT_TOOLS.get(agent, ()):
        return {"error": "Tool is not available to this agent."}, None
    definition = TOOL_REGISTRY[name]
    if context.actor.role not in definition.roles:
        return {"error": "Not authorized for this tool."}, None
    try:
        if isinstance(raw_arguments, str):
            args = definition.args_model.model_validate_json(raw_arguments)
        else:
            args = definition.args_model.model_validate(raw_arguments)
    except (ValidationError, ValueError) as exc:
        return {"error": "Invalid tool arguments.", "validation": str(exc)[:1000]}, None
    try:
        result = definition.handler(context, args)
    except (NotFoundError, ForbiddenError, ValidationFailed) as exc:
        return {"error": str(exc)}, None
    except Exception:
        logger.exception("AI tool %s failed", name)
        return {"error": "Tool failed; no data was returned."}, None
    if isinstance(result, dict) and result.get("kind") == "send_reminder":
        return ({"draft_created": True, "invoice_number": result["invoice_number"], "customer_name": result["customer_name"],
                 "subject": result["subject"], "body": result["body"], "confirmation_required": True}, result)
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json"), None
    if isinstance(result, list):
        return [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in result[:50]], None
    return result, None
