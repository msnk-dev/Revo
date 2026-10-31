"""One-shot smoke check for OpenAI-compatible Ollama tool calling."""

import httpx
from openai import OpenAI

from app.ai.config import settings


def main() -> None:
    if not settings.ollama_model:
        raise SystemExit("OLLAMA_MODEL is empty; no model is configured to verify")
    client = OpenAI(
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key or "ollama",
        timeout=httpx.Timeout(30.0, connect=3.0),
        max_retries=0,
    )
    try:
        response = client.chat.completions.create(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": "Call the verification function now."}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "verify_tool_call",
                    "description": "Return a successful tool-call capability check.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }],
            tool_choice={"type": "function", "function": {"name": "verify_tool_call"}},
        )
    except Exception as exc:
        raise SystemExit(f"Ollama tool check could not reach model {settings.ollama_model}: {type(exc).__name__}; do not rely on it") from None
    calls = response.choices[0].message.tool_calls or []
    if not any(call.function.name == "verify_tool_call" for call in calls):
        raise SystemExit(f"Model {settings.ollama_model} did not return the required tool call; do not rely on it")
    print(f"Ollama model {settings.ollama_model} supports OpenAI-compatible tool calls at {settings.ollama_base_url}.")


if __name__ == "__main__":
    main()
