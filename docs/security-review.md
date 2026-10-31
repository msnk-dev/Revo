# Security checklist review

Reviewed against section 10 of `Revo_Subscription_Management_PROJECT_SPEC.md` on 2026-10-31.

| Spec item | Status | Evidence / remaining note |
|---|---|---|
| Authorization is enforced per customer row | Pass | Customer-facing invoice, payment, subscription, and assistant queries scope by the authenticated customer's `customer_id`. `tests/api/test_security_matrix.py` creates two customers and proves another customer's invoice is hidden. |
| Signup cannot set a role; staff creation is admin-only | Pass | Strict signup schema ignores no unknown fields and always creates a customer; staff creation uses the admin role dependency. Covered by `test_auth.py` and `test_admin_staff.py`. |
| Parameterized queries only, including AI reports | Pass | Application queries use SQLAlchemy expressions and bound values. No user-controlled raw SQL construction was found. The `text()` use in `models/core.py` is a static partial-index predicate. |
| Password hashing, secret handling, and example env values | Pass with deployment note | Passwords use Argon2. `.env.example` contains placeholders; production rejects the built-in/example signing key. Demo seeds generate compliant random passwords and reject weak overrides; the requested `admin123`/`user123` pair is loadable only with `APP_ENV=demo` and an explicit seed flag. Signup/reset always enforce the strong rule. Production still needs an operator-provided private signing key. |
| Restricted CORS, secure cookies/CSRF, login rate limiting, security headers | Pass with scaling note | CORS requires explicit origins and rejects `*`; tests allow the configured local UI origin and reject an attacker origin. Production cookies set `Secure`, auth cookies are `HttpOnly`, mutations use CSRF validation, and login failures are limited to 5 per email/client key per 15-minute window. Responses set `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`. |
| Reset tokens are hashed, single-use, and expire | Pass | Tokens are generated with `secrets`, stored as SHA-256 hashes, expire after 60 minutes, are marked used once, and reset invalidates prior sessions. Reset and weak-password cases are covered by `tests/api/test_auth.py`. |
| Status history and `ai_runs` are the only audit trails | Pass | Subscription transitions write status history and assistant interactions write `ai_runs`; no general-purpose audit log was found. This follows the spec's explicit scope cut. |
| PII sent to the LLM is minimized | Pass | Customer tools scope to the caller and return only needed IDs/names, invoice/payment values, and line data; tool outputs do not include customer email, address, or tax ID. Reminder proposals include a recipient name but resolve the email only after staff confirmation. |

## Remaining open items

- Login throttling is in process memory. Move the counter to shared storage before running multiple API workers or replicas; the current Compose API runs one worker.
- Production deployment still needs a private `APP_SECRET_KEY`, HTTPS termination, and production-only allowed CORS origins. The checked-in Compose defaults are for local development.
- The checklist intentionally excludes a general audit log, as directed by the project spec.
