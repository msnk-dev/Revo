# Revo AI

## Why AI here, and what it deliberately does not do

The assistant makes subscription and invoice data easier to inspect, explains stored invoice line calculations, summarizes the daily CFO report, and drafts collection reminders. Those tasks benefit from natural-language questions and short explanations.

The assistant does not calculate financial values, create invoices, change subscriptions, apply discounts, or send email on its own. Read tools call Revo's typed service functions under the signed-in user's identity. Customer tools are scoped to that account by the service layer. A billing run or reminder is saved as a pending proposal and requires a separate authenticated confirmation request. The normal billing screens and scheduler remain usable with all AI keys unset.

## Architecture

- `backend/app/ai/tools.py` is the allow-listed registry. Every tool validates its arguments with a Pydantic model; the model cannot request SQL or arbitrary Python execution.
- `backend/app/ai/api.py` runs up to four provider/tool steps, bounds tool results, logs runs to `ai_runs`, and exposes chat, action confirmation/rejection, and daily brief endpoints.
- `backend/app/ai/providers.py` uses the OpenAI-compatible SDK with Groq → Hugging Face → Ollama according to `LLM_PROVIDER_ORDER`. It retries transient errors, honors numeric `Retry-After` values, opens a 60-second provider circuit after failure, then uses deterministic local answers when all providers are unavailable.
- `backend/app/ai/briefing.py` builds a payload from report services, stores a daily brief in `briefs`, and replaces provider text with a deterministic template if its numbers are not present in the computed payload.
- Provider output is narration only. Customer names, product descriptions, invoice notes, and tool results are treated as data, never as instructions.

## Endpoints

All paths below are under `/api/v1/ai` and require a signed-in user.

| Method | Path | Access | Purpose |
|---|---|---|---|
| `POST` | `/chat` | Admin, staff, customer | Ask a question; returns an answer and any pending proposals. |
| `POST` | `/actions/{id}/confirm` | Admin, staff | Run the approved billing operation or send the reviewed reminder. |
| `POST` | `/actions/{id}/reject` | Admin, staff | Reject a pending proposal without performing it. |
| `POST` | `/brief/generate` | Admin, staff | Generate or refresh today's deterministic/AI-assisted brief. |
| `GET` | `/brief/latest` | Admin, staff | Read the latest stored daily brief. |

The only write proposals currently implemented are due invoice generation and a reminder for a verified overdue invoice. Proposals are stored in `ai_runs.plan`; only pending records can be confirmed, and a proposal can be confirmed once.

## Configuration

Set values in the root `.env` copied from `.env.example`. Keep secrets private.

| Variable | Default / use |
|---|---|
| `LLM_PROVIDER_ORDER` | `groq,hf,ollama`; names are tried in order. |
| `GROQ_API_KEY` | Empty disables Groq. |
| `GROQ_MODEL` | Empty disables Groq until an explicit model is configured. |
| `HF_TOKEN` | Empty disables Hugging Face. |
| `HF_MODEL` | Empty disables Hugging Face until an explicit model is configured. |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434/v1` for the API in Docker to reach a host Ollama server. For an API running directly on the host, set `http://localhost:11434/v1`. |
| `OLLAMA_MODEL` | Empty disables Ollama until a model supporting tool calling is configured. |
| `OLLAMA_API_KEY` | Local compatibility value; defaults to `ollama`. |
| `LLM_TIMEOUT_S` | `20` seconds for remote providers; Ollama is capped at `3` seconds. |
| `LLM_MAX_RETRIES` | `2` retries for transient provider failures. |
| `LLM_DAILY_TOKEN_BUDGET` | `100000`; an approximate character-based token budget is enforced per UTC day and logged for provider-backed chat and brief runs. |

No provider calls are made when its key and model are unset. In that default setup, chat uses the local report/customer services for supported questions, and the daily brief uses its deterministic fallback. Ollama is optional and must have a pulled model that supports OpenAI-compatible tool calls. The budget uses a character-based token estimate because provider token usage is not returned consistently across all configured models.

## Demo

1. Start the stack with `make up` and seed it with `make seed`.
2. Sign into the frontend as the seeded admin and ask the assistant questions such as “How much is outstanding?”, “List overdue invoices”, or “Explain invoice 1”. The answer uses current local database data even with no AI provider credentials.
3. To try a proposal with a configured provider, ask it to prepare a billing run or draft a reminder for an overdue invoice. Inspect the proposal in the panel, then confirm or reject it explicitly.
4. On the dashboard, select **Generate now** in the daily brief card. Without provider credentials the deterministic brief is stored and displayed with its fallback status.

The frontend is API-backed by default (`VITE_USE_MOCKS=false`). For the limited local mock preview, set `VITE_USE_MOCKS=true`; mock responses never perform write actions.

## Verification

Run `cd backend && uv --cache-dir .uv-cache run --frozen pytest tests/ai -q`. The AI tests cover router registration, the database models, deterministic brief upsert/fallback behavior, and number grounding. Provider integrations require credentials and network access and are not exercised by the local default test suite.
