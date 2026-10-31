# Revo performance smoke results

Measured against the running Docker Compose API with the bulk fixture loaded. These are observed HTTP request timings, not estimates.

- Run time (UTC): `2026-10-31 09:46:39`
- Samples per endpoint: `30` (plus `3` warm-up requests)
- Percentiles: nearest-rank p50 and p95; elapsed time includes HTTP request/response and API serialization.
- Dataset counts are bulk-prefixed records; existing demo records are not included.

| Bulk fixture | Rows |
|---|---:|
| Customers | 1,000 |
| Subscriptions | 2,000 |
| Invoices | 20,000 |
| Payments | 16,000 |

| Endpoint | Status | p50 (ms) | p95 (ms) |
|---|---:|---:|---:|
| `GET /customers` | 200 | 7.3 | 10.6 |
| `GET /admin/staff` | 200 | 6.0 | 7.1 |
| `GET /products` | 200 | 5.5 | 6.5 |
| `GET /products/{id}/variants` | 200 | 6.1 | 7.0 |
| `GET /plans` | 200 | 5.8 | 7.1 |
| `GET /taxes` | 200 | 5.7 | 6.8 |
| `GET /payment-methods` | 200 | 6.4 | 7.4 |
| `GET /quotation-templates` | 200 | 8.8 | 11.0 |
| `GET /discounts` | 200 | 6.7 | 9.6 |
| `GET /subscriptions` | 200 | 13.7 | 15.2 |
| `GET /invoices` | 200 | 9.8 | 12.8 |
| `GET /payments` | 200 | 29.7 | 32.3 |
| `GET /reports/summary (dashboard)` | 200 | 23.2 | 32.3 |
| `GET /reports/subscriptions` | 200 | 9.0 | 10.5 |
| `GET /reports/revenue` | 200 | 26.6 | 29.5 |
| `GET /reports/overdue` | 200 | 28.1 | 103.1 |
| `GET /reports/overdue/summary` | 200 | 7.0 | 8.3 |
| `GET /reports/payments` | 200 | 35.6 | 39.0 |
| `GET /reports/renewal-reminders` | 200 | 7.6 | 9.5 |
| `GET /reports/export.csv` | 200 | 241.5 | 315.7 |
| `GET /admin/jobs/expired-quotations` | 200 | 5.4 | 7.4 |
| `GET /admin/jobs/renewal-reminders` | 200 | 5.3 | 6.7 |
| `GET /ai/brief/latest` | 200 | 5.1 | 5.8 |
| `GET /ai/runs` | 200 | 5.9 | 8.7 |
| `GET /portal/subscriptions` | 200 | 10.1 | 12.2 |
| `GET /portal/invoices` | 200 | 7.0 | 9.3 |
| `GET /portal/payments` | 200 | 8.1 | 10.0 |

## Endpoints over the 2 s p95 threshold

None in this run.
