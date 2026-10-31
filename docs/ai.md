# Revo AI

## Frontend milestone note

The B-M10 frontend includes an assistant panel for signed-in roles and a standalone assistant page. It sends messages to `POST /api/v1/ai/chat`; when `VITE_USE_MOCKS=true`, the mock layer returns a deterministic demo response and performs no actions. The backend AI provider, scoped tools, proposals, and confirmation flow remain for B-M13 and depend on Person A mounting the AI router.
