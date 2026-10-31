# Revo — Subscription Management System — Complete Project Specification

> Hand this entire file to ChatGPT (or any coding LLM) as the first message. It is self-contained.

---

## 0. Instructions to the AI building this

You are the lead engineer. Build the system described below, end to end.

**Context:** hackathon / evaluation demo. Team of 2-4, 2-3 days. A finished, demo-able vertical slice beats a broad unfinished build; where this spec says "required" and time is short, ask me which items to cut rather than silently skipping them.

**Working rules**
1. Build in the milestone order in §15. After each milestone: show the files changed, the commands to run, and the tests that prove it works. Do not move on until I say "next".
2. Do not invent library APIs, flags, or config keys. If unsure that something exists in the version pinned in §3, say so and tell me where to check.
3. Label anything not run as **"untested"**. Never claim code works unless you traced it or I ran it.
4. Where this spec is ambiguous, the decision is already made in §2. If you disagree with a decision, say so *before* implementing, with the concrete flaw.
5. Money is never a float. Business rules live in the service layer, never in route handlers, never in the LLM.
6. Give complete runnable files (no `# rest of code here`). For small edits to existing files, show only the changed section with enough context to place it.
7. Do not add features outside §1 and §14 (out of scope). Mention nice-to-haves separately at the end.
8. Prefer minimal comments; code should be self-explanatory. Keep prose short.

---

## 1. Product summary

**Product name:** Revo (the platform being built).

**Client:** Brightloop Software — sells software on subscription (monthly/yearly), with add-ons and product variants. Customers range from small shops (monthly) to large companies (yearly). Brightloop is the business using Revo; use "Revo" for the app, repo, UI branding and emails.

**Problem today:** spreadsheet subscriptions, missed renewals, hand-typed invoices, payments matched by scrolling bank statements, quarterly manual revenue reports. Nobody knows true recurring revenue.

**Goal:** one platform covering: catalog → plans → quotation → subscription → recurring invoicing → payments → reporting, with customer self-service portal and an AI assistant layer.

**Users**
| Role | Can do |
|---|---|
| Admin | Everything. Only role that can create staff, discounts, taxes, products, plans. |
| Staff (internal) | Day-to-day: customers, quotations, subscriptions, invoices, payments, reports (read). No config, no user management. |
| Customer | Portal only: own subscriptions, own invoices, own payments. Read-mostly. |

---

## 2. Decisions on ambiguities (binding unless I override)

The source brief is silent or vague on these. Implement exactly as stated.

| # | Topic | Decision |
|---|---|---|
| 1 | Password rule "more than eight characters" | **≥ 9 chars**, ≥1 uppercase, ≥1 lowercase, ≥1 special char. Digit **not** required (not in brief). Hash with argon2id or bcrypt. |
| 2 | Public signup | Always creates role `customer` plus a linked `customers` record. The signup endpoint must **ignore any `role` field** in the payload. Staff are created only via `POST /admin/staff` (admin only). |
| 3 | Email uniqueness | Case-insensitive unique on `users.email` (store lowercased; unique index on `lower(email)`). |
| 4 | Password reset | Single-use token, 32+ bytes random, **store only SHA-256 hash**, expires in 60 min, always return the same response whether or not the email exists (no account enumeration). Dev: send via SMTP to MailHog/console. |
| 5 | Currency | Single currency, configurable via `APP_CURRENCY` (default `INR`). The brief's "560" has no currency. |
| 6 | Variants | A product has attributes (e.g. `Brand`) with values (e.g. `Odoo`) each carrying `extra_price` (Odoo = +560). Line unit price = `product.sales_price + Σ selected variant extra_price`. |
| 7 | Plan price vs line price | **Invoices bill from subscription lines only.** `plan.price` is the catalog price and prefills the first line's unit price on creation; it is not billed separately (avoids double-billing). |
| 8 | Plan options | Per plan, admin sets booleans: `auto_close`, `closable`, `pausable`, `renewable`. `auto_close` → a daily job closes subscriptions on that plan at `expiry_date`. Other flags gate which actions the UI/API allows on subscriptions of that plan. |
| 9 | Pause | Modeled as a **flag** (`is_paused`, `paused_at`) on an Active subscription, not a 6th status, so the lifecycle stays Draft→Quotation→Confirmed→Active→Closed. Billing skips paused subscriptions. |
| 10 | Subscription lifecycle | `draft → quotation → confirmed → active → closed`. `confirmed→active` happens automatically when `start_date <= today` (daily job) or manually by staff at/after start. `closed` is terminal. Every transition writes to `subscription_status_history`. |
| 11 | Invoice lifecycle | `draft → confirmed → paid`, plus `cancelled` (from draft or confirmed with no payments). **Overdue is derived**, not stored: `status='confirmed' AND amount_due>0 AND due_date<today`. |
| 12 | Partial payments | Supported. `amount_paid = Σ payments`; invoice → `paid` when `amount_paid >= total`. Overpayment rejected (400). |
| 13 | Discount stacking | **No stacking.** Per invoice line, apply the single applicable discount with the largest saving. Subscription-scope discounts are evaluated on the line subtotal share as a competing candidate per line. |
| 14 | Discount usage limit | Global `max_uses`. Consumed (`uses_count += 1`) when the invoice is **generated**; released (`-= 1`) if that invoice is cancelled. Per-customer limits not in brief → not implemented. |
| 15 | Discount order | Discount first, then tax on the discounted amount. Taxes are **exclusive** (added on top). |
| 16 | Tax rules | Admin defines taxes (name, rate %). Each product has a default tax; subscription line may override. Invoice lines **snapshot** name/price/tax rate so later catalog edits never change past invoices. |
| 17 | Rounding | `NUMERIC(12,2)`, Python `Decimal`, `ROUND_HALF_UP`, round per line then sum. |
| 18 | Billing cadence | `daily/weekly/monthly/yearly`. Monthly/yearly next-date is computed from the **anchor `start_date`** using `dateutil.relativedelta` (Jan 31 → Feb 28 → Mar 31, not drift to 28). |
| 19 | No double/skipped billing | Unique constraint `(subscription_id, period_start)` on invoices. Billing job catches up missed periods one at a time (loop until `next_invoice_date > today`), each in its own transaction. |
| 20 | Quotation template | Has plan, product lines, `validity_days`. Creating a subscription from a template copies lines and sets `quotation_expires_on = today + validity_days`. Expired quotations can't be confirmed. |
| 21 | Payment methods | Admin-managed list; seed: `cash, bank_transfer, card, upi, cheque`. Payments are **recorded manually**; no real gateway integration. |
| 22 | Invoice "send"/"print" | Send = email PDF to customer (SMTP, dev=MailHog). Print = PDF download. |
| 23 | Mid-cycle changes/proration | Not supported. Changing quantity/lines applies from the next invoice. |
| 24 | Customer entity | `customers` is separate from `users` (staff can create customers who have no login). A customer user links via `customers.user_id`. |

---

## 3. Tech stack (pinned recommendation — one choice, not a menu)

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2** | Typed, fast to build, same language as the AI layer |
| DB | **PostgreSQL 16** | Needs transactions, partial/unique indexes, `FOR UPDATE SKIP LOCKED`, window/aggregate SQL |
| Frontend | **React + Vite + TypeScript + Tailwind + TanStack Query + React Router** | Role-based portal + admin app |
| Jobs | **APScheduler** (in-process) for dev/demo | Simplest. Upgrade path: Celery/RQ if you need multiple workers (don't now). |
| Auth | JWT access (15 min) + refresh (7 d) in httpOnly cookies, or bearer tokens; RBAC dependency in FastAPI | |
| PDF | **WeasyPrint** or **ReportLab** (pick WeasyPrint; Jinja2 HTML → PDF) | |
| Email | `aiosmtplib`/stdlib `smtplib`; MailHog in docker-compose | |
| AI | `openai` Python SDK pointed at Groq / Hugging Face OpenAI-compatible endpoints (§11) | One client, swappable base URL |
| Tests | pytest, httpx, pytest-asyncio | |
| Infra | docker-compose: `postgres`, `api`, `web`, `mailhog` | |

Pin exact versions in `pyproject.toml`/`package.json` and tell me which you chose. Do not mix sync and async DB sessions; **use sync SQLAlchemy sessions** unless you have a reason (simpler with APScheduler and transactions).

---

## 4. RBAC matrix

`A`=admin `S`=staff `C`=customer (own data only, enforced by `customer_id` filter in the query, not in the UI)

| Resource | A | S | C |
|---|---|---|---|
| Staff users (create/deactivate) | ✔ | ✘ | ✘ |
| Products, variants, plans | CRUD | read | read (active plans only) |
| Taxes, discounts, payment methods, quotation templates | CRUD | read | ✘ |
| Customers | CRUD | CRUD | own profile read/update |
| Subscriptions | CRUD | CRUD (no delete) | read own; request close if plan `closable` |
| Invoices | all | confirm/cancel/send/print | read/print own |
| Payments | all | record | read own |
| Reports/dashboard | ✔ | ✔ | ✘ |
| AI assistant | all agents | ops agents | customer-scoped agent only |

Every route declares its required role via a dependency. Write a test per route that asserts 401/403/200 per role.

---

## 5. Data model

Use UUID or bigint PKs (pick bigint identity for index speed). All tables: `id, created_at, updated_at`. Soft-delete only for products/plans/customers (`is_active`); never delete invoices/payments.

**users** — `email` (lower, unique), `password_hash`, `role` enum(admin,staff,customer), `is_active`, `last_login_at`
**password_reset_tokens** — `user_id`, `token_hash` (unique), `expires_at`, `used_at`
**customers** — `user_id` (nullable, unique), `name`, `email`, `phone`, `company`, `billing_address`, `tax_id`
**products** — `name`, `type` enum(service, software, addon, physical), `sales_price`, `cost_price`, `notes`, `default_tax_id`, `is_active`
**product_variant_attributes** — `product_id`, `name` (e.g. Brand)
**product_variant_values** — `attribute_id`, `value` (e.g. Odoo), `extra_price` (e.g. 560.00)
**taxes** — `name`, `rate_pct` NUMERIC(5,2), `is_active`
**plans** — `name`, `price`, `billing_period` enum(daily,weekly,monthly,yearly), `min_quantity`, `available_from`, `available_to`, `auto_close`, `closable`, `pausable`, `renewable`, `is_active`
**quotation_templates** — `name`, `plan_id`, `validity_days`
**quotation_template_lines** — `template_id`, `product_id`, `variant_value_ids` (int[] or join table), `quantity`
**subscriptions** — `number` (unique, e.g. `SUB-000123` from a DB sequence), `customer_id`, `plan_id`, `status`, `start_date`, `expiry_date`, `next_invoice_date`, `payment_terms_days` (due = invoice_date + N), `quotation_expires_on`, `is_paused`, `paused_at`, `closed_at`, `created_by`
**subscription_lines** — `subscription_id`, `product_id`, `variant_value_ids`, `description`, `quantity`, `unit_price`, `tax_id`
**subscription_status_history** — `subscription_id`, `from_status`, `to_status`, `changed_by`, `changed_at`
**discounts** — `name`, `type` enum(fixed, percent), `value`, `scope` enum(product, subscription), `min_purchase`, `min_quantity`, `start_date`, `end_date`, `max_uses`, `uses_count`, `is_active`
**discount_products** — `discount_id`, `product_id`
**invoices** — `number` (unique sequence, `INV-…`), `subscription_id`, `customer_id`, `status`, `invoice_date`, `due_date`, `period_start`, `period_end`, `subtotal`, `discount_total`, `tax_total`, `total`, `amount_paid`, `amount_due`, `sent_at`; **UNIQUE(subscription_id, period_start)**
**invoice_lines** — `invoice_id`, `product_id`, `description`, `quantity`, `unit_price`, `discount_id` (nullable), `discount_amount`, `tax_name`, `tax_rate_pct`, `tax_amount`, `line_total`
**payment_methods** — `name`, `is_active`
**payments** — `invoice_id`, `method_id`, `amount` (>0), `paid_on`, `note`, `recorded_by`
**ai_runs** — `agent`, `user_id`, `input`, `plan`(jsonb), `tool_calls`(jsonb), `output`, `model`, `provider`, `latency_ms`, `tokens_in/out`, `status`
**briefs** — `brief_date` (unique), `payload` (jsonb: the exact numbers), `narrative` (text), `model`, `provider`, `used_fallback` (bool)

**Indexes (required for the <2 s target, §9):**
`subscriptions(status)`, `subscriptions(customer_id)`, `subscriptions(next_invoice_date) WHERE status='active' AND NOT is_paused`, `invoices(customer_id, status)`, `invoices(status, due_date)` (overdue), `invoices(invoice_date)`, `payments(invoice_id)`, `payments(paid_on)`, unique `lower(users.email)`, unique `invoices(subscription_id, period_start)`.

DB `CHECK` constraints: `payments.amount > 0`, `discounts.value > 0`, `percent <= 100`, `plans.min_quantity >= 1`, `expiry_date >= start_date`.

---

## 6. Business rules (implement in `services/`, unit-test each)

### 6.1 Auth
- Signup: validate email format, uniqueness, password rule (§2.1). Return 409 on duplicate (acceptable here; the reset flow is the enumeration-safe one).
- Login: rate-limit (e.g. 5 failures / 15 min / IP+email). Inactive users can't log in.
- Reset: `POST /auth/forgot` → always 202; `POST /auth/reset` with token + new password (same rule) → invalidates token and all refresh tokens.

### 6.2 Catalog and plans
- Variant price math per §2.6.
- Plan availability: a plan can only be selected when `available_from <= today <= available_to` (nulls = open).
- `quantity >= plan.min_quantity` enforced on every subscription line sum or per-line (decide per-line; say so in code).

### 6.3 Quotation → subscription
- Create from scratch or from a template (copies plan + lines).
- Transition rules: `draft→quotation` (requires ≥1 line, customer, plan, dates), `quotation→confirmed` (quotation not expired), `confirmed→active` (§2.10), `active→closed` (staff, or customer request if `closable`), plan `renewable` → "renew" creates a **new** subscription (draft) copying lines with `start_date = old.expiry_date + 1 day`; old one is closed when it expires.
- Set `next_invoice_date = start_date` on activation.

### 6.4 Invoice generation (the core)
```
generate_due_invoices(as_of=today):
  rows = SELECT subscriptions WHERE status='active' AND NOT is_paused
         AND next_invoice_date <= as_of AND (expiry_date IS NULL OR next_invoice_date <= expiry_date)
         ORDER BY id  FOR UPDATE SKIP LOCKED  (in batches of ~100)
  for each sub, in its OWN transaction:
     loop while sub.next_invoice_date <= as_of and within expiry:
        period_start = sub.next_invoice_date
        period_end   = advance(period_start, plan.billing_period, anchor=sub.start_date) - 1 day
        build lines (price snapshot) → apply best discount per line → tax → totals
        INSERT invoice(status='draft'); on UNIQUE violation → skip (already billed)
        sub.next_invoice_date = period_end + 1 day
  return {created, skipped_duplicates, failed:[{sub_id, error}]}
```
- One failing subscription must not abort the batch; record it in `failed`.
- Re-running the job immediately must create **zero** new invoices (test this).
- `due_date = invoice_date + sub.payment_terms_days`.
- Invoice actions: `confirm` (draft→confirmed, assigns final number if you defer numbering), `cancel` (releases discount use), `send` (confirmed only), `print`. Editing a confirmed invoice's amounts is forbidden.

### 6.5 Discounts
Eligible when: `is_active`, today in `[start_date,end_date]`, `uses_count < max_uses` (or null), line/sub meets `min_purchase`/`min_quantity`, and (scope=product ⇒ line product in `discount_products`; scope=subscription ⇒ all lines). Fixed amount is capped at the line amount (never negative). Applied automatically at generation; it stops by itself on expiry/exhaustion because eligibility is re-evaluated every generation. Only admin can create/edit.

### 6.6 Payments
Record `invoice_id, method_id, amount, paid_on, note`. Row-lock the invoice (`SELECT … FOR UPDATE`) while updating `amount_paid/amount_due/status` to avoid races. Only `confirmed` invoices accept payments. Reject overpayment.

### 6.7 Reporting definitions (use exactly these)
- **Active subscriptions** = `status='active'` (paused counted separately).
- **MRR** = Σ over active, non-paused subscriptions of (pre-tax recurring line total normalized to a month: daily×30, weekly×52/12, monthly×1, yearly÷12). State the normalization in the UI tooltip.
- **Revenue collected** (period) = Σ `payments.amount` where `paid_on` in period.
- **Invoiced** (period) = Σ `invoices.total` for confirmed/paid with `invoice_date` in period.
- **Outstanding** = Σ `amount_due` of confirmed invoices.
- **Overdue** = §2.11, with days overdue and amount.

---

## 7. API surface (REST, JSON, `/api/v1`, OpenAPI auto-docs)

Standard list params: `page`, `page_size` (max 100), `sort`, `q`, plus filters. Response `{items, total, page, page_size}`. Errors: `{error:{code,message,details}}`.

- **Auth:** `POST /auth/signup`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/forgot`, `/auth/reset`, `GET /auth/me`
- **Admin:** `POST /admin/staff`, `GET /admin/staff`, `PATCH /admin/staff/{id}` (deactivate)
- **Catalog:** `/products`, `/products/{id}/variants`, `/plans`, `/taxes`, `/payment-methods`, `/quotation-templates` (CRUD, role-gated)
- **Discounts:** `/discounts` (admin write; staff read)
- **Customers:** `/customers`
- **Subscriptions:** `/subscriptions` (list/create/get/patch), `POST /subscriptions/from-template/{id}`, `POST /subscriptions/{id}/transition` `{to}`, `/pause`, `/resume`, `/close`, `/renew`
- **Invoices:** `/invoices`, `POST /invoices/generate` (admin/staff manual trigger, supports `dry_run=true`), `POST /invoices/{id}/confirm|cancel|send`, `GET /invoices/{id}/pdf`
- **Payments:** `POST /invoices/{id}/payments`, `GET /payments`
- **Portal (customer-scoped):** `GET /portal/subscriptions|invoices|payments`, `GET /portal/invoices/{id}/pdf`
- **Reports:** `GET /reports/summary?from&to`, `/reports/subscriptions`, `/reports/revenue` (by month), `/reports/payments`, `/reports/overdue`; all accept filters (status, plan, customer, date range) and return paginated rows + totals
- **AI:** `POST /ai/chat` `{message, thread_id?}`, `POST /ai/actions/{proposal_id}/confirm|reject`, `GET /ai/runs` (admin)

---

## 8. Frontend (React)

**Staff/Admin app:** Dashboard (KPI cards: active subs, MRR, collected, outstanding, overdue count; revenue-by-month chart; overdue table), Customers, Subscriptions (list with status chips + filters; detail with lines, status timeline from history, action buttons per allowed transition), Quotation Templates, Invoices (list, detail, confirm/cancel/send/print, record payment dialog), Payments, Reports (filters + summary view + CSV export), Catalog (Products w/ variants, Plans, Taxes, Discounts, Payment methods — admin only), Staff management (admin only), AI Assistant side panel.
**Customer portal:** Login/Signup/Forgot/Reset, My subscriptions (status, next invoice date, close request if allowed), My invoices (paid/outstanding badges, PDF), My payments, AI helper (read-only, scoped).
**UX requirements:** route guards by role (but the API is the real enforcement), server-side pagination everywhere, skeleton loaders, optimistic updates only for non-financial actions, every destructive action behind a confirm dialog, money formatted via `Intl.NumberFormat` from API strings (never parse to float for math).

---

## 9. Performance requirement: every page < 2 s with thousands of subscriptions

Treat as a testable requirement, not an aspiration.
- Server-side pagination only; no endpoint returns unbounded lists.
- Eager-load relations (`selectinload`/`joinedload`); a test asserts query count per list endpoint (no N+1).
- Reports computed with SQL aggregates (`GROUP BY`, `FILTER`), not Python loops. Add a materialized view or summary table **only if** measurements show a miss; refresh on invoice/payment writes or every N minutes.
- Seed script generates **1,000 customers / 2,000 subscriptions / 20,000 invoices / 16,000 payments**; a pytest-benchmark or Locust script asserts **p95 < 2 s** (target < 500 ms API) for dashboard, each list, and each report on that dataset. Report the numbers; if any endpoint misses, show `EXPLAIN ANALYZE` and the fix.
- Billing job must process 1,000 due subscriptions in a reasonable time (report measured number; no promise made here).

---

## 10. Security checklist (verify each, don't assume)

- Authorization enforced server-side per row (customer sees only `customer_id == me.customer.id`; test with two customers).
- Signup cannot set role; staff creation admin-only (test).
- Parameterized queries only (ORM); no string-built SQL — including in the AI report tool (§11).
- Password hashing (argon2id/bcrypt); no secrets in code; `.env.example` with placeholders only.
- CORS restricted; secure/httpOnly cookies if using cookies + CSRF protection; login rate limiting; security headers.
- Reset tokens hashed at rest, single-use, expiring.
- Status history (subscriptions) and `ai_runs` are the only audit trails; no general audit log (cut for hackathon scope).
- PII not sent to the LLM beyond what a tool result requires (§11.6).

---

## 11. AI orchestration layer (Groq / free Hugging Face models)

### 11.1 Design principle (important)
**The LLM never computes money, never writes to the DB directly, and never decides to bill.** Billing runs from the deterministic scheduler/service. Agents *read, explain, classify, draft, and propose*. Anything that changes state is returned as a **proposal** that a human confirms through `POST /ai/actions/{id}/confirm`, which then calls the same service layer and RBAC as the normal UI. If the LLM is down, the whole system still works.

### 11.2 Pattern: orchestrator + specialists (+ evaluator gate)
```
User msg ─► Router/Orchestrator (small, cheap call; JSON output: {agent, intent})
              ├─► Billing Ops Agent      (staff/admin)
              ├─► Collections Agent      (staff/admin)
              ├─► Revenue Insights Agent (staff/admin)
              ├─► Discount Advisor Agent (admin)
              ├─► Invoice Explainer      (all roles; customers only for own invoices)
              └─► Customer Helper Agent  (customer, read-only, own data)
           Each agent: tool-calling loop (max 4 steps) over a WHITELIST of typed tools
           ─► Guard/Evaluator: validate output JSON schema, check proposals vs RBAC + rules
           ─► Response (+ proposals needing confirmation)
```
Keep it a plain Python loop; do **not** add LangChain/CrewAI/AutoGen. A router + `dict[str, Agent]` + a tool registry is enough.

### 11.3 Agents and tools
Tools are Python functions with Pydantic input/output schemas, executed with the **caller's** identity (RBAC applied), returning bounded results (max 50 rows, summarized).

| Agent | Purpose | Tools (all typed, whitelisted) |
|---|---|---|
| Router | Pick agent from intent; reject out-of-scope | none |
| Billing Ops | "Which subscriptions bill this week?", dry-run the billing run, explain failed generations, flag anomalies (price spike vs last invoice, missing tax) | `list_due_subscriptions`, `dry_run_generate_invoices`, `get_failed_runs`, `compare_with_previous_invoice`, **proposal:** `propose_run_billing` |
| Collections | Rank overdue invoices by amount × days, draft reminder emails (tone by days overdue) | `list_overdue_invoices`, `get_customer_payment_history`, **proposal:** `propose_send_reminder` (human approves each email) |
| Revenue Insights | Natural-language questions → numbers | `get_summary(from,to)`, `get_revenue_by_month`, `get_active_subscriptions_breakdown`, `get_overdue_summary`. **No free-form SQL.** The LLM chooses a tool + parameters; the numbers come from the tool; the LLM only phrases them. |
| Discount Advisor | Given a customer + seat count, suggest which *existing* eligible discount applies or what rule to create | `list_eligible_discounts`, `simulate_invoice_with_discount`, **proposal:** `propose_discount_rule` (admin approves; creates nothing itself) |
| Invoice Explainer | "Why is this invoice 14,320?" → plain-language, line-by-line breakdown: price, variant extra, quantity, which discount applied and why it was eligible, tax, total | `get_invoice_breakdown(invoice_id)` (deterministic: returns every line with price, discount name/amount, tax name/rate/amount, totals, and the eligibility reason). The LLM only narrates; it may not state any number absent from the tool output. Customers: own invoices only (enforced in the tool). |
| Customer Helper | "When is my next invoice?", "What am I subscribed to?" (delegates invoice questions to Invoice Explainer) | `get_my_subscriptions`, `get_my_invoices` — hard-scoped to `customer_id` |

### 11.4 Provider layer (one client, two backends, graceful fallback)
Use the `openai` SDK with a swappable `base_url`:

| Provider | `base_url` | Key env | Status |
|---|---|---|---|
| Groq (primary) | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | Endpoint and OpenAI-compatible tool calling **verified** in docs/third-party sources |
| Hugging Face Inference Providers (fallback) | `https://router.huggingface.co/v1` | `HF_TOKEN` | **Believed**, not verified — check HF docs for current URL, free-credit limits, and which models support tool calling |
| None (deterministic fallback) | — | — | Return templated answers from tool outputs; AI panel shows "AI offline" |

Env config (never hardcode model IDs):
```
LLM_PROVIDER_ORDER=groq,hf
GROQ_MODEL=llama-3.3-70b-versatile     # verified to support tool calling; catalog churns, re-check at https://console.groq.com/docs/models
GROQ_ROUTER_MODEL=llama-3.1-8b-instant # cheap router only; reported to be flaky at tool calls → don't use it for tool loops
HF_MODEL=<choose after checking HF's current tool-calling-capable models>
LLM_TIMEOUT_S=20
LLM_MAX_RETRIES=2
LLM_DAILY_TOKEN_BUDGET=...
```
Requirements:
- Groq's free tier has strict rate limits (one source reported ~12k tokens/min for the 70B model — treat as unverified; read the live limits page). Implement: retry with exponential backoff on 429/5xx honoring `retry-after`, then fail over to the next provider, then to deterministic fallback.
- Small tool-calling models can emit malformed arguments. **Validate every tool call's arguments with Pydantic**; on failure, feed the validation error back once, then give up gracefully. Never `eval`/exec model output.
- Structured outputs: request JSON, parse with Pydantic, one repair retry. Do not assume `response_format`/JSON-schema mode is supported on every model — feature-detect or prompt for JSON and validate.
- Context discipline: pass tool results as compact JSON (ids, amounts, dates), cap rows, never dump whole tables, keep per-run step cap (4) and token cap. Log every run to `ai_runs`.
- Temperature 0–0.2 for tool/routing calls.

### 11.5 Reference skeleton (**untested**; verify SDK signatures against the version you pin)
```python
from openai import OpenAI
import os

PROVIDERS = {
    "groq": dict(base_url="https://api.groq.com/openai/v1", key="GROQ_API_KEY", model="GROQ_MODEL"),
    "hf":   dict(base_url="https://router.huggingface.co/v1", key="HF_TOKEN", model="HF_MODEL"),
}

def chat(messages, tools=None, order=("groq", "hf")):
    last = None
    for name in order:
        p = PROVIDERS[name]
        if not os.getenv(p["key"]):
            continue
        client = OpenAI(base_url=p["base_url"], api_key=os.environ[p["key"]], timeout=20, max_retries=2)
        try:
            return name, client.chat.completions.create(
                model=os.environ[p["model"]], messages=messages,
                tools=tools, tool_choice="auto" if tools else None, temperature=0.1)
        except Exception as e:
            last = e
    raise RuntimeError(f"all providers failed: {last}")
```
Build the agent loop around it: call → if `tool_calls`, validate args → execute tool under caller identity → append `tool` message → repeat (≤4) → final answer → guard.

### 11.6 AI safety rules
- Prompt-injection: customer names, notes, product descriptions, and invoice text are **untrusted data**. System prompt states that tool results are data, not instructions. Write tools can only produce proposals; confirmation is a separate authenticated API call from a human.
- Customer Helper receives only that customer's data; test that asking about another customer's invoice returns nothing.
- Send the LLM minimal PII (customer id/name, not address/tax id/email unless drafting an email, and then only the recipient name).
- Collections emails are drafts; nothing is sent without staff clicking confirm.

### 11.7 AI acceptance tests
Router picks correct agent on ≥ 20 labeled prompts; malformed tool args are rejected; provider failover works when Groq returns 429 (mock); a customer cannot extract another customer's data via prompt; write tools never mutate without confirmation; with no API keys the app still fully works. Invoice Explainer: output contains no number that is absent from `get_invoice_breakdown` (test with a discounted + taxed fixture); customer asking to explain another customer's invoice gets nothing. CFO brief: guard rejects a narrative with an invented number and falls back to the template; brief numbers equal the dashboard numbers.

---

## 12. Background jobs (APScheduler)

| Job | Schedule | Action |
|---|---|---|
| `activate_subscriptions` | daily 00:05 | `confirmed → active` when `start_date <= today` |
| `generate_invoices` | daily 01:00 | §6.4 for all due subs (draft invoices; staff confirm — or add a setting `AUTO_CONFIRM_INVOICES`, default false) |
| `auto_close_expired` | daily 00:10 | close subs where plan `auto_close` and `expiry_date < today` |
| `expire_quotations` | daily 00:15 | flag quotations past `quotation_expires_on` |
| `renewal_reminders` | daily | list subscriptions expiring in 7 days (surface on dashboard; AI can draft notices) |
| `daily_cfo_brief` | daily 08:00 (+ manual "Generate now" button for demos) | Compute the numbers with the §6.7 report services → store in `briefs.payload` → LLM writes a short narrative (MRR vs yesterday/last week, new/closed subs, collected, outstanding, top 3 overdue, any anomaly) → **guard: every number in the narrative must appear in `payload` (regex check); on mismatch or LLM failure, store a templated narrative with `used_fallback=true`**. Dashboard shows the latest brief. |

Jobs must be idempotent and safe if run twice or concurrently (`SKIP LOCKED` + unique constraints). Expose a manual trigger for each for demos/tests.

---

## 13. Repository layout

```
revo/
  docker-compose.yml  .env.example  README.md  Makefile
  backend/
    pyproject.toml  alembic/  
    app/
      main.py  config.py  db.py  deps.py(auth,rbac)
      models/  schemas/  api/v1/  services/(auth,catalog,subscriptions,billing,discounts,taxes,payments,reports,pdf,email)
      jobs/  ai/(providers.py, router.py, agents/, tools/, guard.py, schemas.py)
      seed/(demo.py, bulk.py)
    tests/(unit/, api/, perf/, ai/)
  frontend/
    src/(app/, api/, features/{auth,dashboard,customers,subscriptions,invoices,payments,reports,catalog,staff,portal,ai}/, components/)
```

---

## 14. Out of scope (do not build)

Real payment gateways/webhooks, proration, multi-currency, multi-tenant, usage-based/metered billing, dunning automation without human approval, mobile app, SSO/2FA (mention as future), tax-authority e-invoicing.

---

## 15. Build order (stop after each; show tests)

1. **Scaffold:** docker-compose (postgres, mailhog), FastAPI app, Alembic, config, health route, CI-able test setup.
2. **Auth & RBAC:** users, signup with password rule, login/refresh, forgot/reset, admin-only staff creation, RBAC dependency + per-role tests.
3. **Catalog:** products + variants (Odoo +560 test), taxes, plans (flags + availability), payment methods, quotation templates.
4. **Customers & subscriptions:** lifecycle state machine + history, from-template, pause/close/renew, number sequence.
5. **Billing engine:** invoice generation per §6.4 with idempotency, concurrency, catch-up tests; confirm/cancel; tax; rounding tests.
6. **Discounts:** rules, eligibility, auto-apply, usage limit/release, expiry tests.
7. **Payments:** record, partial, overpayment rejection, locking, derived overdue.
8. **Reports & dashboard APIs** with §6.7 definitions + indexes.
9. **PDF + email** (send/print).
10. **Frontend:** auth + role routing → admin/staff screens → portal.
11. **Seed + performance run** (§9) and fix misses.
12. **Jobs** (§12).
13. **AI layer** (§11): providers → tools → router → Revenue Insights agent → Invoice Explainer → CFO brief job + guard → Collections agent (draft + confirm flow) → remaining agents only if time allows → tests.
14. **Hardening:** §10 checklist, README with setup + demo script.

---

## 15b. Work split for 2 people (2-3 days)

Give each person the full spec plus one line: "I own only the items listed for Person X; do not build the rest."

**Ownership (no shared files, so no merge fights)**
- **Person A, backend core:** `backend/` except `app/ai/`. Milestones 1-9, 11, 12 and 14 (hardening).
- **Person B, frontend + AI:** `frontend/` and `backend/app/ai/`. Milestones 10 and 13, plus jobs wiring for the CFO brief.
- Only Person A edits Alembic migrations (avoids multiple migration heads).

**Unblocking B from A (do in the first 3 hours, together)**
1. Milestone 1 scaffold, then A commits the full schema migration for every table in section 5 and the demo seed.
2. Agree the service signatures B's AI tools call, with stub implementations returning fixture data, e.g. `reports.get_summary`, `reports.get_revenue_by_month`, `reports.list_overdue`, `billing.get_invoice_breakdown`. A replaces stubs with real code; B never waits.
3. B builds screens against FastAPI's auto-generated OpenAPI schema (generate a typed TS client from it; check which generator you use and its current CLI) or against mocked responses until A's endpoints land.

**Schedule (compress to 2 days by merging blocks 3 and 4)**
| Block | Person A | Person B |
|---|---|---|
| 0: first 3 h, together | scaffold, schema, seed, stubs | repo/frontend scaffold, Groq key + provider layer |
| 1: day 1 | auth/RBAC, catalog, customers, subscriptions, billing engine + tests | login/signup/reset, role routing, catalog + subscription screens, tool registry + router |
| 2: day 2 | discounts, payments, reports APIs, PDF/email | invoice + payment screens, dashboard, Revenue Insights agent, Invoice Explainer |
| 3: day 3 | jobs, bulk seed + perf run, security checklist | CFO brief + guard, Collections agent + confirm flow, portal, AI panel |
| Last 3 h, together | integration, run the section 17 demo script end to end, freeze | same |

**Rules:** one branch per milestone, merge to `main` every few hours, never merge a red test. Freeze features 3 hours before the demo.

**Cut order if behind (drop top first):** Billing Ops + Discount Advisor agents, Hugging Face fallback, customer-portal polish, invoice email send (keep PDF download), CSV export. Never cut: billing idempotency tests, RBAC tests, discounts, payments, the dashboard numbers, Revenue Insights, Invoice Explainer.

---

## 16. Acceptance tests (minimum)

- Duplicate email (any case) → rejected. Passwords of 8 chars, or missing upper/lower/special → rejected; 9 chars with all three → accepted.
- Signup payload with `role:"admin"` → still `customer`.
- Staff cannot create staff/discounts/taxes; customer cannot reach `/reports/*`; customer A cannot read customer B's invoice (404/403).
- Product with Brand=Odoo variant prices at `sales_price + 560`.
- Billing: run twice → 0 new invoices second time; subscription 3 periods behind → exactly 3 invoices, correct periods; Jan-31 monthly anchor produces Feb 28 then Mar 31; paused/closed/draft subs never billed; one bad sub doesn't stop the batch.
- Discounts: percent and fixed; min qty/purchase; date window; `max_uses` exhaustion stops application; cancel releases a use; no stacking; discount never makes a line negative; tax computed after discount.
- Invoice: totals match hand-calculated fixtures to the cent; confirmed invoice immutable; cancel blocked when payments exist.
- Payments: partial → still confirmed with correct `amount_due`; full → `paid`; overpay → 400; concurrent payments don't corrupt `amount_paid`.
- Reports: figures equal independent SQL on seeded data; overdue list equals §2.11 definition.
- Perf: §9 targets on bulk seed.
- AI: §11.7.

---

## 17. Demo script (for the final walkthrough)

Admin creates product (Odoo variant) + plan + tax + 10% discount (min qty 5) → staff builds subscription from template → confirm → activate → run billing → invoice shows discount + tax → record partial then final payment → dashboard updates → set a past due date to show overdue → Collections Agent drafts reminder → staff approves → customer logs into portal and sees only own data → Revenue Insights answers "how much is outstanding?" with numbers matching the dashboard.

---

## 18. Verification status of claims in this document

- **Verified (from sources checked while writing):** Groq exposes an OpenAI-compatible endpoint at `https://api.groq.com/openai/v1`; `llama-3.3-70b-versatile` is documented as supporting tool calling; Groq has a free tier with strict rate limits and a frequently changing model catalog.
- **Believed, not checked:** Hugging Face router URL and its free limits/tool-calling support; WeasyPrint/APScheduler/dateutil behaviors as described; exact current versions of all libraries.
- **Mine, not from the brief:** every row in §2, the stack choice in §3, the MRR normalization, all AI architecture. Challenge any of them with a concrete reason.
- **Unmeasured:** all performance claims; they must come from the §9 benchmark run.
