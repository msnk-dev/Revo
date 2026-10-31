# Revo AI

## Why AI here, and what it deliberately does not do

The assistant makes subscription and invoice data easier to inspect, explains stored invoice line calculations, summarizes the daily CFO report, and drafts collection reminders. Those tasks benefit from natural-language questions and short explanations.

The assistant does not calculate financial values, create invoices, change subscriptions, apply discounts, or send email on its own. Read tools call Revo's typed service functions under the signed-in user's identity. Customer tools are scoped to that account by the service layer. A billing run or reminder is saved as a pending proposal and requires a separate authenticated confirmation request. The normal billing screens and scheduler remain usable with all AI keys unset.

## Architecture

- `backend/app/ai/tools.py` is the allow-listed registry. Every tool validates its arguments with a Pydantic model; the model cannot request SQL or arbitrary Python execution.
- `backend/app/ai/routing.py` deterministically classifies a prompt to a Pydantic-validated `{agent, intent}` object. Revenue Insights, Invoice Explainer, Collections, Billing Ops, and Discount Advisor receive only their specialist tools.
- `backend/app/ai/api.py` runs at most four provider/tool steps, bounds tool results, logs specialist runs to `ai_runs`, and exposes chat, routing, run history, failed-run explanation, action confirmation/rejection, and daily brief endpoints.
- `backend/app/ai/providers.py` uses the OpenAI-compatible SDK in `LLM_PROVIDER_ORDER`; the demo defaults to Hugging Face first, then Groq, and does not use Ollama. Connect timeout is capped at 3 seconds; failed providers open a 60-second circuit. Provider failures fall back to deterministic local answers.
- `backend/scripts/check_ollama_tools.py` sends a data-free required function-call probe to the configured Ollama model. Run it before relying on a newly pulled model.
- `backend/app/ai/briefing.py` builds a payload from report services, stores a daily brief in `briefs`, and replaces provider text with a deterministic template if its numbers are not present in the computed payload.
- Provider output is narration only. Customer names, product descriptions, invoice notes, and tool results are treated as data, never as instructions.

## Endpoints

All paths below are under `/api/v1/ai` and require a signed-in user.

| Method | Path | Access | Purpose |
|---|---|---|---|
| `POST` | `/chat` | Admin, staff, customer | Ask a question; returns an answer and any pending proposals. |
| `POST` | `/route` | Signed-in user | Return validated specialist and intent JSON. |
| `GET` | `/runs` | Admin | Paginated assistant-run history. |
| `GET` | `/runs/{id}/explanation` | Admin | Explain fallback or failed runs without exposing provider secrets. |
| `POST` | `/actions/{id}/confirm` | Admin, staff; discount-rule proposals require admin | Run the approved billing operation, send the reviewed reminder, or create the reviewed discount rule. |
| `POST` | `/actions/{id}/reject` | Admin, staff | Reject a pending proposal without performing it. |
| `POST` | `/brief/generate` | Admin, staff | Generate or refresh today's deterministic/AI-assisted brief. |
| `GET` | `/brief/latest` | Admin, staff | Read the latest stored daily brief. |

Write tools only create proposals. Billing runs, reminders, and discount-rule creation require a separate confirmation; discount rules can only be confirmed by an admin. Discount simulation and previous-invoice comparison are read-only. Customer invoice comparison and discount simulation derive scope from the signed-in actor inside the tool, not a model-supplied customer ID.

## Configuration

Set values in the root `.env` copied from `.env.example`. Keep secrets private.

| Variable | Default / use |
|---|---|
| `LLM_PROVIDER_ORDER` | `hf,groq`; names are tried in order. Ollama is off in the demo defaults. |
| `GROQ_API_KEY` | Empty disables Groq. |
| `GROQ_MODEL` | `openai/gpt-oss-20b`, verified with a required tool-call request. |
| `GROQ_ROUTER_MODEL` | `openai/gpt-oss-20b`, used for model-assisted route classification. |
| `HF_TOKEN` | Empty disables Hugging Face. Inference may require credits or paid usage, depending on the account. |
| `HF_MODEL` | `Qwen/Qwen3.8-27B:fastest`; HF selects the fastest available provider for this model. |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434/v1` for Docker to reach host Ollama. For an API running directly on the host, use `http://localhost:11434/v1`. |
| `OLLAMA_MODEL` | Empty disables Ollama until a model supporting tool calling is configured. |
| `OLLAMA_API_KEY` | Local compatibility value; defaults to `ollama`. |
| `LLM_TIMEOUT_S` | `20` seconds for remote providers; Ollama is capped at `3` seconds. |
| `LLM_MAX_RETRIES` | `2` retries for transient provider failures. |
| `LLM_DAILY_TOKEN_BUDGET` | `100000`; an approximate character-based token budget is enforced per UTC day and logged for provider-backed chat and brief runs. |

No provider calls are made when its key or model is unset. In that default setup, chat uses local report/customer services for supported questions, and the daily brief uses its deterministic fallback. After pulling/configuring Ollama, run `docker compose exec api python scripts/check_ollama_tools.py`; only rely on the model if the required tool call succeeds. The budget uses a character-based token estimate because provider token usage is not returned consistently across all configured models.

## Demo

1. Start the stack with `make up` and seed it with `make seed`.
2. Sign into the frontend as the seeded admin and ask the assistant questions such as “How much is outstanding?”, “List overdue invoices”, or “Explain invoice 1”. The answer uses current local database data even with no AI provider credentials.
3. To try a proposal with a configured provider, ask it to prepare a billing run or draft a reminder for an overdue invoice. Inspect the proposal in the panel, then confirm or reject it explicitly.
4. On the dashboard, select **Generate now** in the daily brief card. Without provider credentials the deterministic brief is stored and displayed with its fallback status.

The frontend is API-backed by default (`VITE_USE_MOCKS=false`). For the limited local mock preview, set `VITE_USE_MOCKS=true`; mock responses never perform write actions.

## Verification

Run `cd backend && uv --cache-dir .uv-cache run --frozen pytest tests/ai -q`. The AI tests cover 20 labeled routes, malformed tool arguments, mocked Groq 429 failover, cross-customer prompt isolation, approval-only writes, offline fallback, run-history RBAC, and number grounding. Provider integrations require credentials and network access and are otherwise mocked in tests.
