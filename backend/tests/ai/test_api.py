from datetime import date

from sqlalchemy import select

from app.ai import api
from app.ai.models import AIRun
from app.ai.tools import ToolContext, execute_tool
from app.deps import Actor
from app.errors import ForbiddenError


def _login(client, email: str):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword1!"})
    assert response.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}


def test_chat_uses_deterministic_local_report_when_no_provider(client, create_user, db_session, monkeypatch):
    user = create_user("admin@example.com", "admin")
    csrf = _login(client, user.email)
    monkeypatch.setattr(api.ai_settings, "groq_api_key", None)
    monkeypatch.setattr(api.ai_settings, "hf_token", None)
    monkeypatch.setattr(api.ai_settings, "ollama_model", "")

    response = client.post("/api/v1/ai/chat", headers=csrf, json={"message": "How much is outstanding?"})

    assert response.status_code == 200
    assert response.json()["offline"] is True
    assert "Current month report values" in response.json()["answer"]
    run = db_session.scalar(select(AIRun).where(AIRun.agent == "revenue_insights"))
    assert run is not None and run.status == "fallback" and run.user_id == user.id


def test_customer_cannot_call_staff_read_or_write_tools(db_session):
    actor = Actor(user_id=10, role="customer", customer_id=42)
    context = ToolContext(db_session, actor)

    try:
        execute_tool("list_overdue_invoices", {"limit": 10}, context)
    except ForbiddenError:
        pass
    else:
        raise AssertionError("customer should not be allowed to use staff tools")
    try:
        execute_tool("propose_run_billing", {"as_of": date.today().isoformat()}, context)
    except ForbiddenError:
        pass
    else:
        raise AssertionError("customer should not be allowed to propose a billing run")


def test_propose_billing_tool_only_previews(db_session):
    context = ToolContext(db_session, Actor(user_id=1, role="admin", customer_id=None))

    result = execute_tool("propose_run_billing", {"as_of": "2026-10-31"}, context)

    assert result["preview"]["eligible_count"] == 0
    assert context.proposal == {"action": "run_billing", "as_of": "2026-10-31"}
    assert db_session.scalar(select(AIRun)) is None


def test_confirm_pending_billing_action_runs_once(client, create_user, db_session):
    user = create_user("admin@example.com", "admin")
    csrf = _login(client, user.email)
    run = AIRun(
        agent="assistant", user_id=user.id, input="Generate invoices", plan={"proposal": {"action": "run_billing", "as_of": "2026-10-31"}},
        tool_calls=[], output="Pending", status="proposal_pending",
    )
    db_session.add(run)
    db_session.commit()
    action_id = run.id

    first = client.post(f"/api/v1/ai/actions/{action_id}/confirm", headers=csrf)
    second = client.post(f"/api/v1/ai/actions/{action_id}/confirm", headers=csrf)

    assert first.status_code == 200
    assert first.json()["status"] == "confirmed"
    assert second.status_code == 404


def test_chat_rejects_unknown_fields(client, create_user):
    user = create_user("staff@example.com", "staff")
    csrf = _login(client, user.email)

    response = client.post("/api/v1/ai/chat", headers=csrf, json={"message": "hello", "role": "admin"})

    assert response.status_code == 422
    assert "role" in response.json()["error"]["details"]
