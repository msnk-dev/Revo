from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from openai import APIStatusError
from sqlalchemy import select

from app.ai import agents, api, providers
from app.ai.models import AIRun
from app.ai.schemas import ChatIn, DateRangeArgs
from app.ai.tools import ToolContext, execute_tool
from app.deps import Actor
from app.errors import NotFoundError
from app.models import Customer, Invoice, InvoiceLine, Plan, Product, Subscription, User
from app.services import reports


@pytest.mark.parametrize(
    ("message", "role", "expected"),
    [
        ("What is our MRR?", "staff", "revenue_insights"),
        ("How much revenue did we collect?", "admin", "revenue_insights"),
        ("Show outstanding balances", "staff", "revenue_insights"),
        ("Give me collected revenue by month", "admin", "revenue_insights"),
        ("Show subscription count by plan", "staff", "revenue_insights"),
        ("How many subscriptions are active?", "admin", "revenue_insights"),
        ("Summarize monthly revenue", "staff", "revenue_insights"),
        ("What is invoiced this month?", "admin", "revenue_insights"),
        ("Show the overdue summary", "staff", "collections"),
        ("Which invoices are overdue?", "admin", "collections"),
        ("Draft a reminder for invoice #18", "staff", "collections"),
        ("Help with collections", "admin", "collections"),
        ("List overdue invoices", "staff", "collections"),
        ("Which customers need a payment reminder?", "admin", "collections"),
        ("Review past due invoices", "staff", "collections"),
        ("Explain invoice ID 18", "customer", "invoice_explainer"),
        ("Why is invoice number 44 this amount?", "staff", "invoice_explainer"),
        ("Show the tax breakdown for invoice id 12", "customer", "invoice_explainer"),
        ("Explain the discount on invoice number 7", "admin", "invoice_explainer"),
        ("Break down invoice #21 line by line", "staff", "invoice_explainer"),
        ("What is the weather today?", "staff", None),
    ],
)
def test_router_classifies_labeled_intents(message, role, expected):
    assert agents.deterministic_route(message, role)[0] == expected


def test_date_range_tool_schema_uses_frozen_from_to_names():
    schema = DateRangeArgs.model_json_schema()
    assert set(schema["properties"]) == {"from", "to"}
    assert DateRangeArgs.model_validate({"from": "2026-10-01", "to": "2026-10-31"}).date_to == date(2026, 10, 31)


def test_malformed_tool_arguments_are_rejected_without_calling_service():
    actor = Actor(user_id=1, role="staff", customer_id=None)
    output, proposal = execute_tool(
        "get_summary",
        '{"from":"not-a-date","to":"2026-10-31"}',
        ToolContext(db=None, actor=actor, user_message="summary"),
        "revenue_insights",
    )
    assert output["error"] == "Invalid tool arguments."
    assert proposal is None


def _completion(text: str = "ok"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
    )


def _rate_limit_error(retry_after: str = "0") -> APIStatusError:
    response = httpx.Response(
        429,
        headers={"retry-after": retry_after},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    return APIStatusError("rate limited", response=response, body=None)


def test_provider_retries_429_then_succeeds(monkeypatch):
    monkeypatch.setattr(providers.settings, "llm_provider_order", "groq")
    monkeypatch.setattr(providers.settings, "groq_api_key", "test-key")
    monkeypatch.setattr(providers.settings, "groq_model", "test-model")
    monkeypatch.setattr(providers.settings, "llm_max_retries", 1)
    monkeypatch.setattr(providers, "_breaker_until", {})
    delays = []
    monkeypatch.setattr(providers.time, "sleep", delays.append)

    class FakeCompletions:
        calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise _rate_limit_error("0")
            return _completion()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    client = FakeClient()
    monkeypatch.setattr(providers, "OpenAI", lambda **kwargs: client)
    response = providers.chat_completion([{"role": "user", "content": "hello"}])
    assert response is not None and response.provider == "groq"
    assert client.chat.completions.calls == 2
    assert delays == [0.0]


def test_provider_fails_over_from_groq_429_to_huggingface(monkeypatch):
    monkeypatch.setattr(providers.settings, "llm_provider_order", "groq,hf")
    monkeypatch.setattr(providers.settings, "groq_api_key", "groq-key")
    monkeypatch.setattr(providers.settings, "groq_model", "groq-model")
    monkeypatch.setattr(providers.settings, "hf_token", "hf-key")
    monkeypatch.setattr(providers.settings, "hf_model", "hf-model")
    monkeypatch.setattr(providers.settings, "llm_max_retries", 0)
    monkeypatch.setattr(providers, "_breaker_until", {})
    requested = []

    class FakeCompletions:
        def __init__(self, provider):
            self.provider = provider

        def create(self, **kwargs):
            requested.append(kwargs["model"])
            if self.provider == "groq":
                raise _rate_limit_error()
            return _completion()

    class FakeClient:
        def __init__(self, *, base_url, **kwargs):
            provider = "groq" if "groq" in base_url else "hf"
            self.chat = SimpleNamespace(completions=FakeCompletions(provider))

    monkeypatch.setattr(providers, "OpenAI", FakeClient)
    response = providers.chat_completion([{"role": "user", "content": "hello"}])
    assert response is not None and response.provider == "hf"
    assert requested == ["groq-model", "hf-model"]


def test_invoice_explainer_number_guard_rejects_unreturned_amount():
    assert agents._grounded("Invoice total is INR 144.00", {"total": "144.00"})
    assert not agents._grounded("Invoice total is INR 145.00", {"total": "144.00"})


def _create_invoice_fixture(db_session, invoice_id=1):
    owner = User(email=f"owner-{invoice_id}@example.com", password_hash="unused-test-hash", role="customer", is_active=True)
    other_user = User(email=f"other-{invoice_id}@example.com", password_hash="unused-test-hash", role="customer", is_active=True)
    db_session.add_all([owner, other_user])
    db_session.flush()
    owner_customer = Customer(user_id=owner.id, name="Invoice Owner", email=owner.email)
    other = Customer(user_id=other_user.id, name="Invoice Holder", email=other_user.email)
    db_session.add_all([owner_customer, other])
    db_session.flush()

    plan = Plan(name=f"Plan {invoice_id}", price=Decimal("100.00"), billing_period="monthly", min_quantity=1)
    product = Product(name=f"Product {invoice_id}", type="software", sales_price=Decimal("100.00"), cost_price=Decimal("0.00"))
    db_session.add_all([plan, product])
    db_session.flush()
    subscription = Subscription(
        number=f"SUB-AI-{invoice_id}", customer_id=other.id, plan_id=plan.id,
        status="active", start_date=date(2026, 1, 1), is_paused=False,
    )
    db_session.add(subscription)
    db_session.flush()
    invoice = Invoice(
        number=f"INV-AI-{invoice_id}", subscription_id=subscription.id, customer_id=other.id,
        status="confirmed", invoice_date=date(2026, 10, 1), due_date=date(2026, 11, 1),
        period_start=date(2026, 10, 1), period_end=date(2026, 10, 31),
        subtotal=Decimal("100.00"), discount_total=Decimal("10.00"), tax_total=Decimal("16.20"),
        total=Decimal("106.20"), amount_due=Decimal("106.20"),
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add(InvoiceLine(
        invoice_id=invoice.id, product_id=product.id, description="Service", quantity=1,
        unit_price=Decimal("100.00"), variant_extra=Decimal("0.00"), discount_name="Seat discount",
        discount_reason="Eligible quantity", discount_amount=Decimal("10.00"), tax_name="GST",
        tax_rate_pct=Decimal("18.00"), tax_amount=Decimal("16.20"), line_total=Decimal("106.20"),
    ))
    db_session.commit()
    return owner, owner_customer, other, invoice


def test_customer_prompt_cannot_read_another_customers_invoice(db_session, monkeypatch):
    owner, owner_customer, other, invoice = _create_invoice_fixture(db_session, 9001)
    monkeypatch.setattr(agents, "chat_completion", lambda *args, **kwargs: None)
    result = agents.run_agent(
        db_session,
        Actor(user_id=owner.id, role="customer", customer_id=owner_customer.id),
        f"Explain invoice ID {invoice.id}",
    )
    assert "not exist" in result.answer or "not be available" in result.answer
    assert other.email not in result.answer
    assert "106.20" not in result.answer


def test_reminder_is_only_a_proposal_until_staff_confirms(db_session, monkeypatch):
    _, _, _, invoice = _create_invoice_fixture(db_session, invoice_id=11)
    invoice.due_date = date.today() - timedelta(days=1)
    db_session.commit()
    staff = User(email="collections-staff@example.com", password_hash="unused-test-hash", role="staff", is_active=True)
    db_session.add(staff)
    db_session.flush()
    actor = Actor(user_id=staff.id, role="staff", customer_id=None)
    email_calls = []
    monkeypatch.setattr(api.email, "send_plain", lambda **kwargs: email_calls.append(kwargs))
    monkeypatch.setattr(
        api,
        "run_agent",
        lambda db, actor, message: agents.AgentResult(
            agent="collections", intent="collections draft", answer="Reminder drafted; not sent.", status="pending",
            proposal={
                    "kind": "send_reminder", "invoice_id": invoice.id, "invoice_number": invoice.number,
                "customer_name": "Test Customer", "recipient_email": "billing@example.com",
                "subject": "Reminder", "body": "Please review your invoice.",
            },
        ),
    )
    response = api.chat(ChatIn(message="draft reminder"), db_session, actor)
    action_id = int(response.proposals[0].id)
    stored = db_session.get(AIRun, action_id)
    assert stored is not None and stored.status == "pending"
    assert email_calls == []

    confirmed = api.confirm_action(action_id, db_session, actor)
    assert confirmed.status == "sent"
    assert len(email_calls) == 1
    assert db_session.get(AIRun, action_id).status == "sent"
    with pytest.raises(NotFoundError):
        api.confirm_action(action_id, db_session, actor)
    assert len(email_calls) == 1


def test_no_provider_uses_read_only_revenue_fallback(db_session, monkeypatch):
    monkeypatch.setattr(agents, "chat_completion", lambda *args, **kwargs: None)
    summary = SimpleNamespace(
        model_dump=lambda mode: {"active_subscriptions": 2, "mrr": "100.00", "collected": "12.00"}
    )
    monkeypatch.setattr(reports, "get_summary", lambda *args: summary)
    result = agents.run_agent(db_session, Actor(user_id=1, role="staff", customer_id=None), "What is our MRR?")
    assert result.status == "fallback"
    assert '"mrr": "100.00"' in result.answer
    assert db_session.scalars(select(Invoice)).all() == []
