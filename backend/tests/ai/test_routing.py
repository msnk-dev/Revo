import pytest

from app.ai.routing import route_message


@pytest.mark.parametrize(
    ("message", "agent", "intent"),
    [
        ("What is our MRR this month?", "revenue_insights", "revenue_summary"),
        ("Show collected revenue for October", "revenue_insights", "revenue_summary"),
        ("How much is outstanding?", "revenue_insights", "revenue_summary"),
        ("What was invoiced last month?", "revenue_insights", "revenue_summary"),
        ("Give me the active subscription breakdown", "revenue_insights", "revenue_summary"),
        ("Compare revenue with the prior month", "revenue_insights", "revenue_summary"),
        ("Explain invoice 123", "invoice_explainer", "invoice_explanation"),
        ("Show the breakdown for invoice 32", "invoice_explainer", "invoice_explanation"),
        ("Compare invoice 56 with the previous invoice", "invoice_explainer", "compare_previous_invoice"),
        ("What changed from my last invoice?", "invoice_explainer", "compare_previous_invoice"),
        ("List the overdue invoices", "collections", "collections"),
        ("Draft a payment reminder", "collections", "collections"),
        ("Show collection priorities", "collections", "collections"),
        ("What is past due?", "collections", "collections"),
        ("How much is the overdue balance?", "collections", "collections"),
        ("Preview the billing run", "billing_ops", "billing_preview"),
        ("Generate invoices for today", "billing_ops", "billing_preview"),
        ("Run invoice generation", "billing_ops", "billing_preview"),
        ("Simulate a discount for 5 seats", "discount_advisor", "discount_simulation"),
        ("Propose a discount rule", "discount_advisor", "propose_discount_rule"),
    ],
)
def test_router_picks_the_expected_specialist_for_labeled_prompts(message, agent, intent):
    routed = route_message(message)
    assert routed.agent == agent
    assert routed.intent == intent
    assert type(routed).model_validate_json(routed.model_dump_json()) == routed
