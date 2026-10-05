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

# Ordered list of models to try, first to last. OPENROUTER_MODEL (if set)
# is tried first; the rest are fallbacks. Duplicates are removed but order
# is preserved.
#
# Pinned free slugs (nex-agi/nex-n2-pro:free, openai/gpt-oss-*:free, etc.)
# get deprecated/repriced without warning and then 404 forever -- dead
# weight that just burns retries before ever reaching a working model.
# "openrouter/free" is the one entry that actually stays current: it's a
# router that dynamically picks a currently-live free model filtered for
# the capability the request needs (tool calling), so it self-heals as
# OpenRouter's free catalog changes. Keep the fallback list to just that.
_env_model = os.getenv("OPENROUTER_MODEL")
FALLBACK_MODELS = list(dict.fromkeys(filter(None, [
    _env_model,
    "openrouter/free",
])))

DEFAULT_MODEL = FALLBACK_MODELS[0]

RETRIES_PER_MODEL = 2
RETRY_BACKOFF_SECONDS = 1.5


def _api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Check your .env file."
        )
    return api_key


def _build_llm(model: str, temperature: float) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=4096,
        api_key=_api_key(),
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "Synthetic Persona Platform",
        },
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
            schema, method="function_calling"
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
