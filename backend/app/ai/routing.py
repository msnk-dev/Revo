"""Small deterministic intent router; output is validated before use."""

import re

from app.ai.schemas import RouteOut

_INVOICE = re.compile(r"\binvoice\b", re.IGNORECASE)


def route_message(message: str) -> RouteOut:
    text = message.casefold()
    has_invoice = _INVOICE.search(text) is not None
    if "discount" in text or "promotion" in text:
        if any(word in text for word in ("create", "propose", "add", "rule")):
            route = {"agent": "discount_advisor", "intent": "propose_discount_rule"}
        else:
            route = {"agent": "discount_advisor", "intent": "discount_simulation"}
    elif has_invoice and any(word in text for word in ("compare", "previous", "prior", "last invoice", "difference")):
        route = {"agent": "invoice_explainer", "intent": "compare_previous_invoice"}
    elif has_invoice and any(word in text for word in ("explain", "why", "breakdown", "detail")):
        route = {"agent": "invoice_explainer", "intent": "invoice_explanation"}
    elif any(word in text for word in ("overdue", "collection", "reminder", "past due")):
        route = {"agent": "collections", "intent": "collections"}
    elif any(word in text for word in ("billing run", "generate invoices", "run billing", "invoice generation")):
        route = {"agent": "billing_ops", "intent": "billing_preview"}
    elif any(word in text for word in ("revenue", "mrr", "collected", "outstanding", "invoiced", "subscription")):
        route = {"agent": "revenue_insights", "intent": "revenue_summary"}
    elif any(word in text for word in ("my account", "my subscription", "my payment", "my invoice")):
        route = {"agent": "revenue_insights", "intent": "account_help"}
    else:
        route = {"agent": "revenue_insights", "intent": "general_question"}
    return RouteOut.model_validate(route)
