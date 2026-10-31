"""Measure list and dashboard endpoints against a running seeded API."""

import os
import statistics
import time

import httpx


def main() -> None:
    base_url = os.environ.get("REVO_API_URL", "http://localhost:8000/api/v1")
    email = os.environ.get("REVO_ADMIN_EMAIL", "admin@revo.local")
    password = os.environ.get("REVO_ADMIN_PASSWORD")
    if not password:
        raise SystemExit("Set REVO_ADMIN_PASSWORD to the seeded admin password")
    with httpx.Client(base_url=base_url, timeout=10) as client:
        response = client.post("/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        endpoints = {
            "customers": "/customers?page=1&page_size=50",
            "subscriptions": "/subscriptions?page=1&page_size=50",
            "invoices": "/invoices?page=1&page_size=50",
            "discounts": "/discounts?page=1&page_size=50",
            "dashboard": "/reports/summary?from=2025-01-01&to=2025-12-31",
            "revenue": "/reports/revenue?from=2025-01-01&to=2025-12-31",
            "payment_report": "/reports/payments?from=2025-01-01&to=2025-12-31&page=1&page_size=50",
        }
        failures = []
        for label, path in endpoints.items():
            elapsed = []
            for _ in range(15):
                started = time.perf_counter()
                result = client.get(path)
                result.raise_for_status()
                elapsed.append((time.perf_counter() - started) * 1000)
            ordered = sorted(elapsed)
            p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
            print(f"{label}: p95={p95:.1f}ms median={statistics.median(elapsed):.1f}ms")
            if p95 >= 2000:
                failures.append(label)
        if failures:
            raise SystemExit("p95 >= 2s: " + ", ".join(failures))


if __name__ == "__main__":
    main()
