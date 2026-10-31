from datetime import date
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.ai import api
from app.ai.models import AIRun
from app.ai.tools import ToolContext, available_tools, execute_tool
from app.deps import Actor
from app.errors import NotFoundError
from app.models import Customer, Discount, Invoice, Plan, Product, Subscription


def _login(client, email: str):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword1!"})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}


def test_route_endpoint_returns_validated_specialist_json(client, create_user):
    user = create_user("route-admin@example.com", "admin")
    headers = _login(client, user.email)
    response = client.post("/api/v1/ai/route", headers=headers, json={"message": "Compare invoice 123 with the previous invoice"})
    assert response.status_code == 200
    assert response.json() == {"agent": "invoice_explainer", "intent": "compare_previous_invoice"}


def test_malformed_tool_arguments_are_rejected(db_session):
    context = ToolContext(db_session, Actor(user_id=1, role="admin", customer_id=None))
    with pytest.raises(ValidationError):
        execute_tool("get_invoice_breakdown", {"invoice_id": -1}, context)


def test_customer_cannot_extract_another_customers_invoice_via_prompt(client, create_user, db_session, monkeypatch):
    owner_user = create_user("prompt-owner@example.com", "customer")
    other_user = create_user("prompt-other@example.com", "customer")
    other_customer = db_session.scalar(select(Customer).where(Customer.user_id == other_user.id))
    plan = Plan(name="Prompt plan", price=Decimal("25.00"), billing_period="monthly", is_active=True)
    product = Product(name="Private invoice service", type="service", sales_price=Decimal("25.00"), cost_price=Decimal("0.00"), is_active=True)
    db_session.add_all([plan, product])
    db_session.flush()
    subscription = Subscription(
        number="SUB-PROMPT-OTHER", customer_id=other_customer.id, plan_id=plan.id, status="active",
        start_date=date.today(), is_paused=False,
    )
    db_session.add(subscription)
    db_session.flush()
    invoice = Invoice(
        number="INV-SECRET-777", subscription_id=subscription.id, customer_id=other_customer.id, status="paid",
        invoice_date=date.today(), due_date=date.today(), period_start=date.today(), period_end=date.today(),
        subtotal=Decimal("25.00"), discount_total=Decimal("0.00"), tax_total=Decimal("0.00"),
        total=Decimal("25.00"), amount_paid=Decimal("25.00"), amount_due=Decimal("0.00"),
    )
    db_session.add(invoice)
    db_session.commit()

    owner_headers = _login(client, owner_user.email)
    tool_call = SimpleNamespace(
        id="call-cross-customer",
        function=SimpleNamespace(name="get_invoice_breakdown", arguments=json.dumps({"invoice_id": invoice.id})),
    )
    first_message = SimpleNamespace(
        content=None, tool_calls=[tool_call], model_dump=lambda exclude_none=True: {"role": "assistant"},
    )
    final_message = SimpleNamespace(content="I cannot access that invoice.", tool_calls=[])
    responses = iter([("mock", "mock-model", first_message, 1), ("mock", "mock-model", final_message, 1)])
    monkeypatch.setattr(api, "chat_completion", lambda *_args: next(responses))

    response = client.post(
        "/api/v1/ai/chat", headers=owner_headers, json={"message": f"Explain invoice {invoice.id}"},
    )
    assert response.status_code == 200
    assert "INV-SECRET-777" not in response.json()["answer"]
    assert "25.00" not in response.json()["answer"]


def test_previous_invoice_comparison_is_same_subscription_and_customer_scoped(create_user, db_session):
    user = create_user("compare-owner@example.com", "customer")
    other_user = create_user("compare-other@example.com", "customer")
    customer = db_session.scalar(select(Customer).where(Customer.user_id == user.id))
    other = db_session.scalar(select(Customer).where(Customer.user_id == other_user.id))
    plan = Plan(name="Compare plan", price=Decimal("30.00"), billing_period="monthly", is_active=True)
    db_session.add(plan)
    db_session.flush()
    subscription = Subscription(number="SUB-COMPARE", customer_id=customer.id, plan_id=plan.id,
                                status="active", start_date=date(2026, 1, 1), is_paused=False)
    db_session.add(subscription)
    db_session.flush()
    previous = Invoice(
        number="INV-COMPARE-1", subscription_id=subscription.id, customer_id=customer.id, status="paid",
        invoice_date=date(2026, 1, 31), due_date=date(2026, 1, 31), period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31), subtotal=Decimal("30.00"), discount_total=Decimal("0.00"),
        tax_total=Decimal("0.00"), total=Decimal("30.00"), amount_paid=Decimal("30.00"), amount_due=Decimal("0.00"),
    )
    current = Invoice(
        number="INV-COMPARE-2", subscription_id=subscription.id, customer_id=customer.id, status="confirmed",
        invoice_date=date(2026, 2, 28), due_date=date(2026, 2, 28), period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28), subtotal=Decimal("30.00"), discount_total=Decimal("0.00"),
        tax_total=Decimal("0.00"), total=Decimal("30.00"), amount_paid=Decimal("0.00"), amount_due=Decimal("30.00"),
    )
    db_session.add_all([previous, current])
    db_session.commit()
    customer_actor = Actor(user_id=user.id, role="customer", customer_id=customer.id)
    comparison = execute_tool("compare_with_previous_invoice", {"invoice_id": current.id}, ToolContext(db_session, customer_actor))
    assert comparison["current"]["invoice_number"] == "INV-COMPARE-2"
    assert comparison["previous"]["invoice_number"] == "INV-COMPARE-1"
    other_actor = Actor(user_id=other_user.id, role="customer", customer_id=other.id)
    with pytest.raises(NotFoundError):
        execute_tool("compare_with_previous_invoice", {"invoice_id": current.id}, ToolContext(db_session, other_actor))


def test_discount_simulation_is_read_only_and_rule_requires_admin_confirmation(client, create_user, db_session):
    user = create_user("discount-ai-admin@example.com", "admin")
    headers = _login(client, user.email)
    product = Product(name="AI simulation product", type="service", sales_price=Decimal("100.00"), cost_price=Decimal("0.00"), is_active=True)
    db_session.add(product)
    db_session.commit()

    actor = Actor(user_id=user.id, role="admin", customer_id=None)
    context = ToolContext(db_session, actor)
    simulation = execute_tool("simulate_discount", {"product_id": product.id, "quantity": 5}, context)
    assert simulation["subtotal"] == "500.00"
    assert simulation["discount_amount"] == "0.00"
    assert db_session.scalar(select(Discount)) is None

    proposal = execute_tool("propose_discount_rule", {
        "name": "AI 10 percent", "type": "percent", "value": "10.00", "scope": "product",
        "min_purchase": "0.00", "min_quantity": 5, "start_date": None, "end_date": None,
        "max_uses": None, "product_ids": [product.id],
    }, context)
    assert proposal["proposal"] == "Discount rule prepared for admin confirmation"
    assert context.proposal["action"] == "create_discount_rule"
    assert db_session.scalar(select(Discount)) is None

    run = AIRun(
        agent="discount_advisor", user_id=user.id, input="Propose 10 percent", plan={"proposal": context.proposal},
        tool_calls=[], output="Pending", status="proposal_pending",
    )
    db_session.add(run)
    db_session.commit()
    response = client.post(f"/api/v1/ai/actions/{run.id}/confirm", headers=headers)
    assert response.status_code == 200, response.text
    created = db_session.scalar(select(Discount))
    assert created is not None and created.name == "AI 10 percent" and created.min_quantity == 5
    simulated = execute_tool("simulate_discount", {"product_id": product.id, "quantity": 5}, context)
    assert simulated["discount_name"] == "AI 10 percent"
    assert simulated["discount_amount"] == "50.00"


def test_ai_runs_are_admin_only_and_fallback_runs_have_explanations(client, create_user, db_session):
    admin = create_user("runs-admin@example.com", "admin")
    staff = create_user("runs-staff@example.com", "staff")
    run = AIRun(
        agent="revenue_insights", user_id=admin.id, input="What is MRR?",
        plan={"failure_reason": "groq: request failed (RateLimitError)"}, tool_calls=[],
        output="Used fallback", status="fallback",
    )
    db_session.add(run)
    db_session.commit()
    run_id = run.id

    _login(client, staff.email)
    assert client.get("/api/v1/ai/runs").status_code == 403

    _login(client, admin.email)
    listed = client.get("/api/v1/ai/runs?page=1&page_size=10")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == run_id
    explanation = client.get(f"/api/v1/ai/runs/{run_id}/explanation")
    assert explanation.status_code == 200
    assert "RateLimitError" in explanation.json()["explanation"]


def test_staff_discount_tools_cannot_propose_a_rule():
    staff = Actor(user_id=7, role="staff", customer_id=None)
    names = {tool.name for tool in available_tools(staff, "discount_advisor")}
    assert "simulate_discount" in names
    assert "propose_discount_rule" not in names


def test_chat_falls_back_when_provider_number_is_not_grounded(client, create_user, monkeypatch):
    user = create_user("guard-admin@example.com", "admin")
    headers = _login(client, user.email)
    monkeypatch.setattr(api, "_provider_answer", lambda *_args: ("Revenue was 999999.", "mock", "mock", []))
    response = client.post("/api/v1/ai/chat", headers=headers, json={"message": "What is collected revenue?"})
    assert response.status_code == 200
    assert "999999" not in response.json()["answer"]
