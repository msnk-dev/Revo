# Backend decisions

## Block 0

- Use synchronous SQLAlchemy sessions with PostgreSQL because the scheduler and billing transactions depend on explicit row locks.
- Use bigint-style integer identity keys and join tables for selected product variants, keeping referential integrity and allowing variant choices to be queried without array parsing.
- Keep the Block 0 service functions as fixed fixtures until their milestone replaces them; interfaces stay stable for Person B's AI tools.
- Use ReportLab for local PDF generation and stdlib SMTP for MailHog email to avoid a browser/system-library dependency in the API container.

## M2 — Authentication and RBAC

- Access and refresh JWTs are HttpOnly SameSite cookies to fit the shared web client; unsafe cookie-authenticated requests require a matching readable CSRF cookie and `X-CSRF-Token` header.
- A user token version revokes refresh sessions on logout, password reset, and staff deactivation; the access token remains short lived at 15 minutes.
- Login failures are counted in process memory by normalized email and client IP, matching the single-process demo setup without adding a dependency.
- Reset tokens have 32 bytes of random entropy, only their SHA-256 hashes are stored, and they expire after 60 minutes. The forgot-password response is identical for known and unknown accounts.

## M3 — Catalog

- Product variant values use foreign-key join tables and are checked against the selected product before price calculation; the Odoo value adds 560.00 to the selected line price.
- Customer catalog reads filter inactive products and plans in the service layer. Staff can read taxes, payment methods, and quotation templates; only admins can change them.
- Plan availability dates are inclusive. Subscription minimum quantity will be checked per line in M4.

## M4 — Customers and subscriptions

- The plan minimum is enforced on each subscription line, as permitted by the brief. The first line uses `plan.price` as its base and still adds selected variant extras; later lines use the product sales price plus extras.
- Scratch subscriptions start as drafts; template-created subscriptions start as quotations and expire `validity_days` after creation. Every status change, including the initial status, is recorded in history. Pause and resume only change the active-subscription flag.
- Renewals create a new draft starting the day after the old expiry, preserving the existing line price and tax snapshots; the old subscription keeps its current expiry and billing schedule.
- Subscription number allocation uses the PostgreSQL sequence and skips any existing formatted number, including the manually numbered demo seed record.

## M5 — Billing engine

- Invoice line snapshots keep the base unit price and selected variant extra separately. Tax and discount names, rates, values, and reasons are copied onto each invoice line so catalog edits do not rewrite historical invoices; migration 0004 adds the snapshot columns.
- Month and year billing boundaries are recalculated from the original subscription start anchor, avoiding Jan 31 drift. Invoice generation commits each subscription separately and catches up each due period in order.
- `uses_count` is consumed once per discount per generated invoice, even when the same discount wins on multiple lines; cancelling an unpaid invoice releases that single use.

## M6 — Discounts

- A product discount must name at least one active product; subscription discounts apply to every line as competing per-line candidates. Only the largest saving wins per line and a fixed saving is capped at that line's pre-tax amount.
- The frozen eligibility service estimates minimum purchase from product sales price times quantity because its signature has no line-total argument. Invoice generation evaluates the actual subscription line total before applying the discount.

## M7 — Payments

- Payments update invoice balances while holding the invoice row lock. Partial payments leave a confirmed invoice open; a zero balance changes it to paid, and overpayments are rejected.

## M8 — Reports and portal

- Report MRR is calculated from recurring subscription lines before tax and excludes paused subscriptions. Daily, weekly, monthly, and yearly values normalize by 30, 52/12, 1, and 1/12 respectively.
- Customer invoice, subscription, payment, and PDF reads always filter by the actor's linked customer ID; a missing or mismatched row returns not found.

## M9 — PDF and email

- Invoice PDFs are generated on demand with ReportLab from invoice-line snapshots. Sending is available only for confirmed invoices and attaches the same PDF; SMTP failures leave `sent_at` unchanged so staff can retry.

## M11 — Performance fixture

- The bulk fixture uses reserved `bulk-` customer emails and `BULK-` invoice/subscription numbers. It refuses a second run until the development database is reset instead of deleting existing records.
- List response relationships are fetched in bounded pages; subscription and discount page details are batch-loaded to keep query counts constant per page.

## M12 — Background jobs

- The scheduler is disabled by default in local settings and explicitly enabled in Docker Compose. Jobs are safe to retry: activation and closure select only eligible rows and every status change writes history.
- Expired quotations remain quotations; expiry is represented by `quotation_expires_on` and surfaced as a queryable flag, so they cannot be confirmed but the lifecycle state history stays within the five specified statuses.

## M14 — Hardening

- Demo account passwords are generated for a new local database or supplied through `REVO_DEMO_ADMIN_PASSWORD` and `REVO_DEMO_CUSTOMER_PASSWORD`; the seed never prints a newly generated password when the admin already exists.
- Production settings reject both the built-in development signing key and the `.env.example` placeholder. Browser cookie mutations use double-submit CSRF validation; bearer-token clients remain compatible.
- The login failure limiter is process-local, so a multi-worker production deployment should move that counter to shared storage before scaling beyond the single API worker used in Compose.

