"""Measure every list/report endpoint against the running bulk-seeded API.

Run inside the API container with REVO_PERF_INTERNAL_AUTH=1 to mint short-lived
benchmark tokens from the locally seeded admin and customer accounts. No
password is required or changed. The measured requests still travel over HTTP
through the running API server.
"""

from __future__ import annotations

import math
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Customer, Invoice, Payment, Subscription, User

SAMPLES = int(os.environ.get("REVO_PERF_SAMPLES", "30"))
WARMUPS = int(os.environ.get("REVO_PERF_WARMUPS", "3"))
DATE_RANGE = "from=2025-01-01&to=2025-12-31"


@dataclass
class Probe:
    name: str
    path: str
    role: str = "admin"


def _benchmark_tokens() -> dict[str, str]:
    """Create regular signed access tokens from local seeded identities."""
    if os.environ.get("REVO_PERF_INTERNAL_AUTH") != "1":
        raise RuntimeError("Set REVO_PERF_INTERNAL_AUTH=1 when running inside the API container")

    from app.services import auth

    tokens: dict[str, str] = {}
    with SessionLocal() as db:
        for email, expected_role in (("admin@example.com", "admin"), ("customer@example.com", "customer")):
            user = db.scalar(select(User).where(func.lower(User.email) == email, User.is_active.is_(True)))
            if user is None or user.role != expected_role:
                raise RuntimeError(f"Required active seeded {expected_role} account is missing: {email}")
            access, _refresh = auth.create_tokens(auth._identity(db, user), user.token_version)
            tokens[expected_role] = access
    return tokens


def _row_counts() -> dict[str, int]:
    with SessionLocal() as db:
        return {
            "customers": db.scalar(select(func.count()).select_from(Customer).where(Customer.email.like("bulk-%@revo.local"))) or 0,
            "subscriptions": db.scalar(select(func.count()).select_from(Subscription).where(Subscription.number.like("BULK-SUB-%"))) or 0,
            "invoices": db.scalar(select(func.count()).select_from(Invoice).where(Invoice.number.like("BULK-INV-%"))) or 0,
            "payments": db.scalar(select(func.count()).select_from(Payment).join(Invoice).where(Invoice.number.like("BULK-INV-%"))) or 0,
        }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def _probe(client: httpx.Client, probe: Probe, token: str) -> tuple[float, float, int]:
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(WARMUPS):
        response = client.get(probe.path, headers=headers)
        response.raise_for_status()

    elapsed: list[float] = []
    status_code = 0
    for _ in range(SAMPLES):
        started = time.perf_counter()
        response = client.get(probe.path, headers=headers)
        elapsed.append((time.perf_counter() - started) * 1000)
        status_code = response.status_code
        response.raise_for_status()
    return _percentile(elapsed, 0.50), _percentile(elapsed, 0.95), status_code


def _markdown(rows: list[tuple[str, float, float, int]], counts: dict[str, int]) -> str:
    lines = [
        "# Revo performance smoke results",
        "",
        "Measured against the running Docker Compose API with the bulk fixture loaded. These are observed HTTP request timings, not estimates.",
        "",
        f"- Run time (UTC): `{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}`",
        f"- Samples per endpoint: `{SAMPLES}` (plus `{WARMUPS}` warm-up requests)",
        "- Percentiles: nearest-rank p50 and p95; elapsed time includes HTTP request/response and API serialization.",
        "- Dataset counts are bulk-prefixed records; existing demo records are not included.",
        "",
        "| Bulk fixture | Rows |",
        "|---|---:|",
    ]
    for label, key in (("Customers", "customers"), ("Subscriptions", "subscriptions"), ("Invoices", "invoices"), ("Payments", "payments")):
        lines.append(f"| {label} | {counts[key]:,} |")
    lines.extend(["", "| Endpoint | Status | p50 (ms) | p95 (ms) |", "|---|---:|---:|---:|"])
    for name, p50, p95, status_code in rows:
        lines.append(f"| `{name}` | {status_code} | {p50:.1f} | {p95:.1f} |")
    over = [(name, p95) for name, _p50, p95, _status in rows if p95 > 2000]
    lines.extend(["", "## Endpoints over the 2 s p95 threshold", ""])
    if over:
        lines.extend(["The following endpoints need an `EXPLAIN (ANALYZE, BUFFERS)` review and query/index follow-up:", ""])
        lines.extend(f"- `{name}`: p95 `{p95:.1f} ms`" for name, p95 in over)
    else:
        lines.append("None in this run.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    base_url = os.environ.get("REVO_API_URL", "http://127.0.0.1:8000/api/v1")
    if SAMPLES < 20:
        raise SystemExit("Use at least 20 samples per endpoint for a meaningful p95")
    tokens = _benchmark_tokens()
    counts = _row_counts()
    expected = {"customers": 1000, "subscriptions": 2000, "invoices": 20000, "payments": 16000}
    if counts != expected:
        raise SystemExit(f"Bulk fixture counts do not match expected values: {counts}; expected {expected}")

    admin = httpx.Client(base_url=base_url, timeout=60)
    customer = httpx.Client(base_url=base_url, timeout=60)
    try:
        response = admin.get("/products?page=1&page_size=1", headers={"Authorization": f"Bearer {tokens['admin']}"})
        response.raise_for_status()
        product_id = response.json()["items"][0]["id"]
        probes = [
            Probe("GET /customers", "/customers?page=1&page_size=50"),
            Probe("GET /admin/staff", "/admin/staff?page=1&page_size=50"),
            Probe("GET /products", "/products?page=1&page_size=50"),
            Probe("GET /products/{id}/variants", f"/products/{product_id}/variants"),
            Probe("GET /plans", "/plans?page=1&page_size=50"),
            Probe("GET /taxes", "/taxes?page=1&page_size=50"),
            Probe("GET /payment-methods", "/payment-methods?page=1&page_size=50"),
            Probe("GET /quotation-templates", "/quotation-templates?page=1&page_size=50"),
            Probe("GET /discounts", "/discounts?page=1&page_size=50"),
            Probe("GET /subscriptions", "/subscriptions?page=1&page_size=50"),
            Probe("GET /invoices", "/invoices?page=1&page_size=50"),
            Probe("GET /payments", "/payments?page=1&page_size=50"),
            Probe("GET /reports/summary (dashboard)", f"/reports/summary?{DATE_RANGE}"),
            Probe("GET /reports/subscriptions", "/reports/subscriptions"),
            Probe("GET /reports/revenue", f"/reports/revenue?{DATE_RANGE}"),
            Probe("GET /reports/overdue", "/reports/overdue?limit=1000"),
            Probe("GET /reports/overdue/summary", "/reports/overdue/summary"),
            Probe("GET /reports/payments", f"/reports/payments?{DATE_RANGE}&page=1&page_size=50"),
            Probe("GET /reports/renewal-reminders", "/reports/renewal-reminders"),
            Probe("GET /reports/export.csv", f"/reports/export.csv?{DATE_RANGE}"),
            Probe("GET /admin/jobs/expired-quotations", "/admin/jobs/expired-quotations"),
            Probe("GET /admin/jobs/renewal-reminders", "/admin/jobs/renewal-reminders"),
            Probe("GET /ai/brief/latest", "/ai/brief/latest"),
            Probe("GET /ai/runs", "/ai/runs?page=1&page_size=50"),
            Probe("GET /portal/subscriptions", "/portal/subscriptions?page=1&page_size=50", "customer"),
            Probe("GET /portal/invoices", "/portal/invoices?page=1&page_size=50", "customer"),
            Probe("GET /portal/payments", "/portal/payments?page=1&page_size=50", "customer"),
        ]
        rows = []
        for probe in probes:
            client = customer if probe.role == "customer" else admin
            p50, p95, status_code = _probe(client, probe, tokens[probe.role])
            rows.append((probe.name, p50, p95, status_code))
            print(f"{probe.name}: p50={p50:.1f}ms p95={p95:.1f}ms status={status_code}")
        output_path = Path(os.environ.get("REVO_PERF_OUTPUT", "../docs/perf.md"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_markdown(rows, counts), encoding="utf-8")
        print(f"Wrote measured results to {output_path.resolve()}")
        over = [(name, p95) for name, _p50, p95, _status in rows if p95 > 2000]
        if over:
            raise SystemExit("p95 over 2 s: " + ", ".join(f"{name} ({p95:.1f} ms)" for name, p95 in over))
    finally:
        admin.close()
        customer.close()


if __name__ == "__main__":
    main()
