from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import logging
import re
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.models import AIRun, Brief
from app.ai.providers import BriefCompletion, generate_brief
from app.models import Subscription
from app.services import reports

logger = logging.getLogger(__name__)
_NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?%?")


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _summary_data(summary) -> dict:
    return summary.model_dump(mode="json")


def _subscription_changes(db: Session, report_date: date) -> tuple[int, int]:
    start = datetime.combine(report_date, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    created = db.scalar(
        select(func.count(Subscription.id)).where(Subscription.created_at >= start, Subscription.created_at < end)
    ) or 0
    closed = db.scalar(
        select(func.count(Subscription.id)).where(Subscription.closed_at >= start, Subscription.closed_at < end)
    ) or 0
    return int(created), int(closed)


def _build_payload(db: Session, report_date: date) -> dict:
    today_summary = reports.get_summary(db, report_date, report_date)
    yesterday = report_date - timedelta(days=1)
    yesterday_summary = reports.get_summary(db, yesterday, yesterday)
    week_summary = reports.get_summary(db, report_date - timedelta(days=6), report_date)
    overdue_summary = reports.get_overdue_summary(db)
    top_overdue = reports.list_overdue(db, limit=3)
    new_subscriptions, closed_subscriptions = _subscription_changes(db, report_date)

    return {
        "brief_date": report_date.isoformat(),
        "current": _summary_data(today_summary),
        "previous_day": {
            "collected": str(yesterday_summary.collected),
            "invoiced": str(yesterday_summary.invoiced),
        },
        "week_to_date": {
            "collected": str(week_summary.collected),
            "invoiced": str(week_summary.invoiced),
        },
        "new_subscriptions_today": new_subscriptions,
        "closed_subscriptions_today": closed_subscriptions,
        "overdue": {
            "count": overdue_summary.count,
            "amount_due": str(overdue_summary.amount_due),
            "top_three": [item.model_dump(mode="json") for item in top_overdue],
        },
        "mrr_comparison": None,
        "anomaly_assessment": "unavailable_from_current_report_contract",
    }


def _numeric_values(value: object) -> set[Decimal]:
    serialized = json.dumps(value, sort_keys=True, default=str)
    values: set[Decimal] = set()
    for match in _NUMBER.findall(serialized):
        token = match.replace(",", "").rstrip("%")
        try:
            values.add(Decimal(token).normalize())
        except InvalidOperation:
            continue
    return values


def _narrative_numbers_are_grounded(narrative: str, payload: dict) -> bool:
    allowed = _numeric_values(payload)
    for match in _NUMBER.findall(narrative):
        token = match.replace(",", "").rstrip("%")
        try:
            if Decimal(token).normalize() not in allowed:
                return False
        except InvalidOperation:
            return False
    return True


def _fallback_narrative(payload: dict) -> str:
    current = payload["current"]
    overdue = payload["overdue"]
    return (
        f"Daily CFO brief for {payload['brief_date']}: current MRR is INR {current['mrr']}; "
        f"collected today is INR {current['collected']}; outstanding is INR {current['outstanding']}. "
        f"There are {overdue['count']} overdue invoices totaling INR {overdue['amount_due']}. "
        f"New subscriptions today: {payload['new_subscriptions_today']}; "
        f"closed subscriptions today: {payload['closed_subscriptions_today']}. "
        "Historical MRR comparison and anomaly assessment are unavailable from the current report contract."
    )


def _make_run(
    *,
    report_date: date,
    payload: dict,
    narrative: str,
    provider_result: BriefCompletion | None,
    used_fallback: bool,
    latency_ms: int,
) -> AIRun:
    return AIRun(
        agent="cfo_brief",
        user_id=None,
        input=f"Generate the read-only daily CFO brief for {report_date.isoformat()}",
        plan={"mode": "read_only_summary", "brief_date": report_date.isoformat()},
        tool_calls=[
            "reports.get_summary",
            "reports.get_overdue_summary",
            "reports.list_overdue(limit=3)",
            "subscription_created_and_closed_counts",
        ],
        output=narrative,
        model=provider_result.model if provider_result else None,
        provider=provider_result.provider if provider_result else None,
        latency_ms=latency_ms,
        tokens_in=None,
        tokens_out=None,
        status="fallback" if used_fallback else "success",
    )


def _save_brief(db: Session, report_date: date, payload: dict, narrative: str, used_fallback: bool,
                provider_result: BriefCompletion | None, run: AIRun) -> None:
    for attempt in range(2):
        existing = db.scalar(select(Brief).where(Brief.brief_date == report_date).with_for_update())
        if existing is None:
            db.add(Brief(
                brief_date=report_date,
                payload=payload,
                narrative=narrative,
                model=provider_result.model if provider_result else None,
                provider=provider_result.provider if provider_result else None,
                used_fallback=used_fallback,
            ))
        else:
            existing.payload = payload
            existing.narrative = narrative
            existing.model = provider_result.model if provider_result else None
            existing.provider = provider_result.provider if provider_result else None
            existing.used_fallback = used_fallback
        db.add(run if attempt == 0 else _make_run(
            report_date=report_date,
            payload=payload,
            narrative=narrative,
            provider_result=provider_result,
            used_fallback=used_fallback,
            latency_ms=run.latency_ms or 0,
        ))
        try:
            db.commit()
            return
        except IntegrityError:
            db.rollback()
            if attempt == 1:
                raise


def _record_failure(db: Session, report_date: date, exc: Exception) -> None:
    db.rollback()
    try:
        db.add(AIRun(
            agent="cfo_brief",
            user_id=None,
            input=f"Generate the read-only daily CFO brief for {report_date.isoformat()}",
            plan={"mode": "read_only_summary", "brief_date": report_date.isoformat()},
            tool_calls=[],
            output=f"Brief generation failed: {type(exc).__name__}: {str(exc)[:500]}",
            status="failed",
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not persist failed CFO brief run for %s", report_date)


def run_daily_brief(db: Session) -> None:
    report_date = _today_utc()
    started = perf_counter()
    try:
        payload = _build_payload(db, report_date)
        provider_result = generate_brief(payload)
        if provider_result and _narrative_numbers_are_grounded(provider_result.narrative, payload):
            narrative = provider_result.narrative
            used_fallback = False
        else:
            if provider_result:
                logger.warning("AI CFO brief contained a number outside its report payload; using deterministic fallback")
            narrative = _fallback_narrative(payload)
            used_fallback = True
            provider_result = None

        latency_ms = int((perf_counter() - started) * 1000)
        run = _make_run(
            report_date=report_date,
            payload=payload,
            narrative=narrative,
            provider_result=provider_result,
            used_fallback=used_fallback,
            latency_ms=latency_ms,
        )
        _save_brief(db, report_date, payload, narrative, used_fallback, provider_result, run)
        logger.info("Saved daily CFO brief for %s (fallback=%s)", report_date, used_fallback)
    except Exception as exc:
        logger.exception("Daily CFO brief failed for %s", report_date)
        _record_failure(db, report_date, exc)
