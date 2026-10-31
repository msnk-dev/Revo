# Brightloop — Shared Contract and Git Protocol (both people attach this + the main spec)

Purpose: two people build in parallel without touching the same files. Conflicts are prevented by **path ownership**, a **frozen interface**, and a **script that fails if you touch someone else's path**. Person A commits this file as `docs/contracts.md`.

---

## 1. Path ownership (every path has exactly one owner)

| Path | Owner |
|---|---|
| `frontend/src/features/{catalog,customers,reports,staff}/**` | **A** (starts after Block 0; see Person A prompt) |
| `frontend/**` (everything else) | **B** |
| `backend/app/ai/**`, `backend/tests/ai/**`, `docs/ai.md` | **B** |
| everything else (`backend/**` otherwise, `docker-compose.yml`, `Makefile`, `.env.example`, `README.md`, `scripts/**`, `.githooks/**`, `.github/**`, `CODEOWNERS`, `docs/contracts.md`, root dotfiles) | **A** |

Notes:
- Only **A** writes Alembic migrations (prevents multiple heads).
- Only **A** edits `backend/pyproject.toml` and its lockfile; only **B** edits `frontend/package.json` and its lockfile. Lockfiles are the #1 source of merge conflicts, so they have one owner each.
- Do not run formatters/linters/codemods over the whole repo. Run them only on your own paths.
- Never rename or move a file you don't own.

## 2. Frozen interface (set in Block 0; **additive changes only** afterwards)

A rename, removal, or signature change needs both humans to agree in chat first. Adding a new function or a new optional field is fine.

**`backend/app/deps.py` (A)**
```python
@dataclass(frozen=True)
class Actor:
    user_id: int
    role: Literal["admin", "staff", "customer"]
    customer_id: int | None

def get_db() -> Iterator[Session]            # sync SQLAlchemy 2.x
def get_current_actor() -> Actor             # FastAPI dependency, 401 if missing/invalid
def require_roles(*roles: str)               # dependency returning Actor, 403 otherwise
```

**`backend/app/errors.py` (A):** `NotFoundError`, `ForbiddenError`, `ValidationFailed`.

**Service functions B's AI tools call (A owns; Block 0 ships stubs that return fixed fixture data, A replaces bodies and never changes signatures):**
```python
reports.get_summary(db, date_from: date, date_to: date) -> SummaryOut
reports.get_revenue_by_month(db, date_from: date, date_to: date) -> list[MonthRevenueOut]
reports.get_active_subscriptions_breakdown(db) -> BreakdownOut
reports.list_overdue(db, limit: int = 50) -> list[OverdueInvoiceOut]
reports.get_overdue_summary(db) -> OverdueSummaryOut
billing.dry_run_generate(db, as_of: date) -> DryRunOut
billing.generate_due_invoices(db, as_of: date) -> GenerateResultOut
billing.get_invoice_breakdown(db, actor: Actor, invoice_id: int) -> InvoiceBreakdownOut
    # customer actors: raise NotFoundError if the invoice isn't theirs
customers.get_payment_history(db, customer_id: int, limit: int = 20) -> list[PaymentOut]
subscriptions.list_for_customer(db, customer_id: int) -> list[SubscriptionOut]
invoices.list_for_customer(db, customer_id: int, status: str | None = None) -> list[InvoiceOut]
discounts.list_eligible(db, customer_id: int, quantity: int, product_id: int | None = None) -> list[DiscountOut]
email.send_plain(to: str, subject: str, body: str) -> None
```
Return models live in `backend/app/schemas/contract.py` (Pydantic v2, A owns). Money fields are `Decimal`, serialized as strings. `InvoiceBreakdownOut` must contain, per line: description, quantity, unit_price, variant_extra, discount_name, discount_amount, discount_reason, tax_name, tax_rate_pct, tax_amount, line_total; plus invoice-level subtotal, discount_total, tax_total, total.

**Hooks between the two code areas**
- `backend/app/main.py` (A) mounts `app.ai.api.router` at `/api/v1/ai`. `backend/app/ai/api.py` (B) must always export `router`.
- `backend/app/jobs/scheduler.py` (A) calls `from app.ai.briefing import run_daily_brief` at 08:00. `run_daily_brief(db) -> None` (B). Block 0 ships a no-op placeholder.
- AI tables `ai_runs` and `briefs` are created in A's initial migration. Their models live in `backend/app/ai/models.py` (B owns the file; A's `alembic/env.py` imports it). B needs a column change → send A a REQUEST (§3); A writes the migration.
- AI config is read by B from its own `backend/app/ai/config.py` (pydantic-settings, env vars from the main spec §11.4). B never edits `app/config.py`. A pre-populates `.env.example` with all `LLM_*`, `GROQ_*`, `HF_*`, `OLLAMA_*` keys in Block 0.
- Frontend ↔ backend contract is the FastAPI OpenAPI schema (`/openapi.json`). A changes endpoints additively only. B regenerates the typed client into `frontend/src/api/generated/` (B-owned, committed).

## 3. Change-request protocol (instead of "just this once" edits)

If you need a change in a path you don't own, **do not edit it.** Send your teammate this message and keep working against a stub or mock:
```
REQUEST  from: <A|B>   file/area: <path>
need: <one sentence>
exact change: <signature / field / dependency / env var>
blocking me? <yes: since when | no>
```
The owner answers "done in <commit>" or "no, because …". Dependencies: B needs a backend package → REQUEST to A; A needs an npm package → REQUEST to B.

## 4. Git rules

- One branch per milestone: `a/m5-billing`, `b/m13-revenue-agent`. Small PRs; merge to `main` at least every ~3 hours.
- Rebase, don't merge: `git fetch origin && git rebase origin/main` before pushing. Never force-push `main`. Warning: `git push --force` rewrites remote history; use `--force-with-lease` and only on your own branch.
- Before every push, `scripts/check_ownership.sh <A|B>` must pass (the pre-push hook runs it).
- `.gitattributes`: `* text=auto eol=lf` (prevents Windows/macOS line-ending conflicts). Commit `.editorconfig` too.
- Never commit `.env`, API keys, `node_modules`, `__pycache__`, `.venv`, build output.
- Generated files (OpenAPI client, lockfiles) are committed only by their owner.
- Never merge a red test. Freeze features 3 hours before the demo; after the freeze only bug fixes, each touching only your own paths.
- **Both people commit and open PRs from day 0** (A: backend scaffold, B: frontend scaffold). The other person reviews every PR (`CODEOWNERS` assigns it). Nobody commits on behalf of the other, and neither person is the repo's sole manager; judges look at `git shortlog -sn` and the PR list. Use conventional commit messages (`feat(billing): ...`, `fix(ui): ...`).
- Docs: A owns `docs/decisions.md` and `docs/erd.md`; B owns `docs/ai.md`.

## 5. Block 0 (first ~3 hours; A leads, B pairs, then each goes solo)

A commits, in this order, and tells B "Block 0 merged":
1. Repo root files: `.gitignore`, `.gitattributes`, `.editorconfig`, `.env.example`, `docker-compose.yml` (postgres, mailhog, api), `Makefile`, `README.md` stub, `CODEOWNERS`, `docs/contracts.md` (this file), `scripts/check_ownership.sh`, `.githooks/pre-push`.
2. Backend scaffold with **all** dependencies installed up front (so nobody edits `pyproject.toml` later): FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pydantic-settings, psycopg driver, password hashing lib, python-jose/PyJWT, APScheduler, python-dateutil, WeasyPrint or ReportLab, `openai` SDK, pytest, httpx.
3. `deps.py`, `errors.py`, `schemas/contract.py`, service stubs per §2, the initial migration for **every** table in main-spec §5 (including `ai_runs`, `briefs`), the demo seed script.
4. Placeholder `backend/app/ai/{__init__,api,models,briefing,config}.py` (empty router, models for the two tables, no-op `run_daily_brief`).
5. `backend/tests/contract/test_signatures.py`: asserts the §2 signatures with `inspect.signature` against a stored snapshot so an accidental change fails CI. (**Untested until written and run.**)

B in parallel (using `BLOCK0=1`, since it creates placeholder folders owned by A later): frontend scaffold, `src/app/routes.tsx` registry, placeholder `index.tsx` + `nav.ts` for each of A's four feature folders, shared components, API client setup.

## 6. `scripts/check_ownership.sh` (tested in a throwaway repo: 7 cases pass)

```bash
#!/usr/bin/env bash
set -euo pipefail
role="${1:?usage: scripts/check_ownership.sh A|B [base-ref]}"
base="${2:-origin/main}"
[ "${BLOCK0:-0}" = "1" ] && exit 0
owner_of() {
  case "$1" in
    frontend/src/features/catalog/*|frontend/src/features/customers/*|frontend/src/features/reports/*|frontend/src/features/staff/*) echo A ;;
    frontend/*|backend/app/ai/*|backend/tests/ai/*|docs/ai.md) echo B ;;
    *) echo A ;;
  esac
}
bad=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  o="$(owner_of "$f")"
  if [ "$o" != "$role" ]; then echo "NOT YOURS ($o owns): $f"; bad=1; fi
done < <(git diff --name-only --no-renames "$base"...HEAD)
[ "$bad" = 0 ] && echo "ownership OK for $role"
exit "$bad"
```

`.githooks/pre-push` (**untested**, thin wrapper):
```bash
#!/usr/bin/env bash
git fetch -q origin main
exec scripts/check_ownership.sh "$(git config brightloop.role)" origin/main
```
Each person once: `git config core.hooksPath .githooks && git config brightloop.role A` (or `B`). Make both files executable (`chmod +x`). Limits: it only checks paths, not file contents, and anyone can bypass with `git push --no-verify`; the real protection is the habit plus PR review via `CODEOWNERS`.

`CODEOWNERS` (later lines win on GitHub; replace handles):
```
*                                        @handle-A
/frontend/                               @handle-B
/frontend/src/features/catalog/          @handle-A
/frontend/src/features/customers/        @handle-A
/frontend/src/features/reports/          @handle-A
/frontend/src/features/staff/            @handle-A
/backend/app/ai/                         @handle-B
/backend/tests/ai/                       @handle-B
/docs/ai.md                              @handle-B
```

## 7. Where conflicts can still happen (honest list)

- Both edit the same file by mistake → the hook catches it before push.
- A changes an endpoint shape without telling B → B's generated client breaks at build time; the additive-only rule plus the signature test limit this.
- Two people create the same placeholder in Block 0 → that's why A creates the AI placeholders and B creates the frontend placeholders, and nobody else touches them until "Block 0 merged".
- Docs: only A edits `README.md`; B documents AI in `docs/ai.md` and A links it.
