from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi import APIRouter
from sqlalchemy import func, select

from app.ai import models
from app.ai.api import router
from app.ai import briefing
from app.models import Base, Invoice, Payment, Subscription


def test_ai_router_is_exported_and_application_imports():
    from app.main import app

    assert isinstance(router, APIRouter)
    assert app is not None


def test_ai_models_match_initial_migration():
    assert set(models.AIRun.__table__.columns.keys()) == {
        "id", "created_at", "updated_at", "agent", "user_id", "input", "plan", "tool_calls",
        "output", "model", "provider", "latency_ms", "tokens_in", "tokens_out", "status",
    }
    assert set(models.Brief.__table__.columns.keys()) == {
        "id", "created_at", "updated_at", "brief_date", "payload", "narrative", "model", "provider",
        "used_fallback",
    }
    assert models.AIRun.__table__.c.user_id.foreign_keys.pop().target_fullname == "users.id"
    assert "ix_ai_runs_created_at" in {index.name for index in models.AIRun.__table__.indexes}
    assert "ai_runs" in Base.metadata.tables and "briefs" in Base.metadata.tables


def test_daily_brief_uses_fallback_and_upserts_without_business_writes(db_session, monkeypatch):
    report_day = date(2026, 10, 30)
    summary = SimpleNamespace(
        model_dump=lambda mode: {
            "active_subscriptions": 2,
            "paused_subscriptions": 0,
            "mrr": "200.00",
            "collected": "50.00",
            "invoiced": "80.00",
            "outstanding": "30.00",
            "overdue_count": 1,
        },
        collected=Decimal("50.00"),
        invoiced=Decimal("80.00"),
    )
    monkeypatch.setattr(briefing, "_today_utc", lambda: report_day)
    monkeypatch.setattr(briefing.reports, "get_summary", lambda *args: summary)
    monkeypatch.setattr(
        briefing.reports,
        "get_overdue_summary",
        lambda *args: SimpleNamespace(count=1, amount_due=Decimal("30.00")),
    )
    monkeypatch.setattr(briefing.reports, "list_overdue", lambda *args, **kwargs: [])
    monkeypatch.setattr(briefing, "generate_brief", lambda payload: None)

    briefing.run_daily_brief(db_session)
    briefing.run_daily_brief(db_session)

    briefs = db_session.scalars(select(models.Brief)).all()
    runs = db_session.scalars(select(models.AIRun)).all()
    assert len(briefs) == 1, (
        "Expected one saved CFO brief; AI run records were: "
        f"{[(run.status, run.output) for run in runs]}"
    )
    assert briefs[0].brief_date == report_day
    assert briefs[0].used_fallback is True
    assert briefs[0].payload["mrr_comparison"] is None
    assert briefs[0].payload["anomaly_assessment"] == "unavailable_from_current_report_contract"
    assert len(runs) == 2
    assert all(run.status == "fallback" for run in runs)
    for business_model in (Invoice, Payment, Subscription):
        assert db_session.scalar(select(func.count()).select_from(business_model)) == 0


def test_daily_brief_rejects_narrative_with_ungrounded_numbers():
    assert not briefing._narrative_numbers_are_grounded("Revenue increased by 999.", {"revenue": "12.00"})
    assert briefing._narrative_numbers_are_grounded("Collected INR 12.00.", {"revenue": "12.00"})
