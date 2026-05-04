"""Azure OpenAI LLM service wrapper with structured JSON output support."""

import json
import logging
import threading
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from openai import AzureOpenAI
from backend.config import get_settings

logger = logging.getLogger(__name__)

_client: AzureOpenAI | None = None
_client_lock = threading.Lock()
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Jinja2 environment for .j2 templates — auto-reloads on file change
_jinja_env = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _get_client() -> AzureOpenAI:
    """Thread-safe lazy singleton for Azure OpenAI client."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:  # double-check after acquiring lock
                settings = get_settings()
                _client = AzureOpenAI(
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                    azure_endpoint=settings.azure_openai_endpoint,
                    max_retries=3,  # automatic retry with exponential backoff for 429/503
                    timeout=120.0,
                )
    return _client


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def render_template(template_file: str, **kwargs) -> str:
    """Render a Jinja2 template (.j2) from the prompts directory."""
    tpl = _jinja_env.get_template(template_file)
    return tpl.render(**kwargs)


def chat_json(
    system_prompt_file: str,
    user_message: str,
    temperature: float = 0.1,
    max_completion_tokens: int = 4096,
) -> dict:
    """Send a chat completion request and parse the JSON response."""
    client = _get_client()
    settings = get_settings()
    system_prompt = _load_prompt(system_prompt_file)

    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    # Log token usage for cost tracking
    if response.usage:
        logger.info(
            "LLM usage: prompt=%d completion=%d total=%d (model=%s)",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            response.usage.total_tokens,
            settings.azure_openai_deployment,
        )

    content = response.choices[0].message.content

    # Guard against truncated/malformed JSON from hitting max_completion_tokens
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error (possibly truncated response): %s. Content: %s…", e, content[:200])
        # Fail closed: return degraded flag so callers know the result is not trustworthy.
        # For compliance workflows, empty violations must never mean "content is clean."
        return {
            "violations": [], "rules": [], "change_log": [],
            "summary": "LLM response was truncated or malformed.",
            "_degraded": True,
        }


def get_embedding(text: str) -> list[float]:
    """Get embedding vector for a text string."""
    client = _get_client()
    settings = get_settings()

    response = client.embeddings.create(
        model=settings.azure_openai_embeddings_deployment,
        input=text,
    )
    return response.data[0].embedding
