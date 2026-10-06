"""
Single place that builds LLM clients and invokes them.

OpenRouter's free tier is unreliable in practice: specific model slugs get
pulled/deprecated without warning ("No endpoints found"), some models leak
internal safety-check tokens instead of real content, and some silently
return near-empty output. Betting on any single slug -- pinned or the
"openrouter/free" auto-router -- has repeatedly broken in different ways.

So instead of picking one model and hoping, every LLM call here goes through
invoke_structured()/invoke_chat(), which retries transient failures and, if a
model keeps failing, automatically falls back to the next model in
FALLBACK_MODELS. The whole pipeline only fails if every candidate model fails.
"""
import os
import time
import logging

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

log_ = logging.getLogger(__name__)

HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen3-8B")

FALLBACK_MODELS = [HF_MODEL]

DEFAULT_MODEL = HF_MODEL

RETRIES_PER_MODEL = 2
RETRY_BACKOFF_SECONDS = 1.5


def _api_key() -> str:
    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        raise RuntimeError(
            "HF_TOKEN is not set. Check your .env file."
        )
    return api_key

def _build_llm(model: str, temperature: float) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=4096,
        api_key=_api_key(),
        base_url="https://router.huggingface.co/v1",   # pehle openrouter.ai tha
    )


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    Plain client bound to the first candidate model, no retry/fallback.
    Kept for callers that don't need structured output. Prefer
    invoke_structured() / invoke_chat() below wherever possible -- they add
    automatic retry and model fallback that this does not.
    """
    return _build_llm(DEFAULT_MODEL, temperature)


def _invoke_with_fallback(build_chain, inputs, temperature: float, label: str):
    last_exc: Exception | None = None
    for model in FALLBACK_MODELS:
        chain = build_chain(model, temperature)
        for attempt in range(1, RETRIES_PER_MODEL + 1):
            try:
                result = chain.invoke(inputs)
                if result is None:
                    # Some free models silently answer in plain text instead of
                    # calling the required tool/function; LangChain's structured-
                    # output parser then returns None instead of raising. Treat
                    # that as a failure too, so it gets retried/failed-over
                    # exactly like an exception, instead of propagating None
                    # into agent code that expects a real schema instance.
                    raise ValueError(
                        "model returned no structured output (did not call the "
                        "required tool/function -- likely responded in plain text instead)"
                    )
                return result
            except Exception as e:  # noqa: BLE001 - intentionally broad, see module docstring
                last_exc = e
                log_.warning(
                    "%s: model=%s attempt=%d/%d failed: %s",
                    label, model, attempt, RETRIES_PER_MODEL, e,
                )
                if attempt < RETRIES_PER_MODEL:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        log_.warning("%s: model=%s exhausted retries, trying next model", label, model)

    raise RuntimeError(
        f"{label}: all candidate models failed ({', '.join(FALLBACK_MODELS)})"
    ) from last_exc


def invoke_structured(prompt, schema, inputs, temperature: float = 0.7, label: str = "llm_call"):
    """
    Build `prompt | llm.with_structured_output(schema, method="function_calling")`
    for each candidate model, retrying transient errors and falling back to
    the next model on failure. Raises RuntimeError (with the last exception
    chained) only if every model/attempt fails.
    """
    def build_chain(model, temperature):
        structured_llm = _build_llm(model, temperature).with_structured_output(
            schema, method="json_schema"
        )
        return prompt | structured_llm

    return _invoke_with_fallback(build_chain, inputs, temperature, label)


def invoke_chat(prompt, inputs, temperature: float = 0.7, label: str = "llm_call"):
    """
    Same retry + model-fallback behavior as invoke_structured(), for plain
    (non-structured) chat calls such as persona interview turns.
    """
    def build_chain(model, temperature):
        return prompt | _build_llm(model, temperature)

    return _invoke_with_fallback(build_chain, inputs, temperature, label)


# =====================================================================
# Milestone 3 additions: async calls, timeouts, global concurrency cap,
# typed errors, embeddings. Milestone-2 sync functions above are untouched.
# =====================================================================
import asyncio

from config import settings


class LLMError(RuntimeError):
    """Controlled LLM failure. kind: timeout | rate_limit | invalid_output | unavailable."""

    def __init__(self, message: str, kind: str = "unavailable"):
        super().__init__(message)
        self.kind = kind


_semaphores: dict = {}


def _llm_semaphore() -> asyncio.Semaphore:
    """One cap on in-flight LLM calls per event loop (controlled concurrency, never unlimited)."""
    loop = asyncio.get_running_loop()
    sem = _semaphores.get(loop)
    if sem is None:
        sem = _semaphores[loop] = asyncio.Semaphore(settings.LLM_MAX_CONCURRENCY)
    return sem


def _classify(exc: Exception) -> str:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "timeout"
    text = str(exc).lower()
    if "429" in text or "rate limit" in text or "rate_limit" in text:
        return "rate_limit"
    if "validation" in text or "no structured output" in text or "parse" in text:
        return "invalid_output"
    return "unavailable"


async def _ainvoke_with_fallback(build_chain, inputs, temperature: float, label: str):
    last_exc: Exception | None = None
    kind = "unavailable"
    for model in FALLBACK_MODELS:
        chain = build_chain(model, temperature)
        for attempt in range(1, RETRIES_PER_MODEL + 1):
            try:
                async with _llm_semaphore():
                    result = await asyncio.wait_for(chain.ainvoke(inputs), timeout=settings.LLM_TIMEOUT_SECONDS)
                if result is None:
                    raise ValueError("model returned no structured output")
                return result
            except Exception as e:  # noqa: BLE001
                last_exc, kind = e, _classify(e)
                log_.warning("%s: model=%s attempt=%d/%d failed (%s): %s", label, model, attempt, RETRIES_PER_MODEL, kind, e)
                if attempt < RETRIES_PER_MODEL:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt * (3 if kind == "rate_limit" else 1))
    raise LLMError(f"{label}: all candidate models failed ({', '.join(FALLBACK_MODELS)})", kind) from last_exc


async def ainvoke_structured(prompt, schema, inputs, temperature: float = 0.7, label: str = "llm_call"):
    """Async twin of invoke_structured(): returns a validated Pydantic `schema` instance or raises LLMError."""
    def build_chain(model, temperature):
        return prompt | _build_llm(model, temperature).with_structured_output(schema, method="function_calling")

    return await _ainvoke_with_fallback(build_chain, inputs, temperature, label)


async def aembed(texts: list[str]) -> list[list[float]] | None:
    """Embeddings via OpenRouter. Returns None when EMBEDDING_MODEL is unset (semantic memory disabled)."""
    if not settings.EMBEDDING_MODEL or not texts:
        return None
    from langchain_openai import OpenAIEmbeddings
    emb = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=_api_key(), base_url="https://openrouter.ai/api/v1",
                           check_embedding_ctx_length=False)
    try:
        return await asyncio.wait_for(emb.aembed_documents(texts), timeout=settings.LLM_TIMEOUT_SECONDS)
    except Exception as e:  # noqa: BLE001 - embeddings are an optimisation; callers fall back to lexical retrieval
        log_.warning("embedding call failed, falling back to lexical retrieval: %s", e)
        return None
