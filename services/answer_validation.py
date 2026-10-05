"""Deterministic (non-LLM) checks: typed-value normalisation per question type + cheap realism/demographic heuristics.
These run BEFORE the LLM validator so obviously bad answers never cost a validation call."""
import re
from dataclasses import dataclass, field
from typing import Any

from schemas_m3 import PersonaAnswer


class AnswerFormatError(ValueError):
    pass


@dataclass
class QuestionSpec:
    key: str
    text: str
    type: str
    options: list[str] | None = None
    scale_min: int = 1
    scale_max: int = 5


LIKERT_LABELS = {1: "strongly disagree", 2: "disagree", 3: "neutral", 4: "agree", 5: "strongly agree"}


def format_instructions(q: QuestionSpec) -> str:
    t = q.type
    if t == "yes_no":
        return "Set `value` to true (yes) or false (no). Put a short explanation in `answer`."
    if t in ("rating", "likert"):
        extra = " (1=strongly disagree … 5=strongly agree)" if t == "likert" and (q.scale_min, q.scale_max) == (1, 5) else ""
        return f"Set `value` to an integer from {q.scale_min} to {q.scale_max}{extra}. Put a short reason in `answer`."
    if t == "numeric":
        return "Set `value` to a single number (no units, no ranges). Put any context in `answer`."
    if t == "single_choice":
        return f"Set `value` to EXACTLY one of: {q.options}. Put a short reason in `answer`."
    if t == "multiple_choice":
        return f"Set `value` to a list containing one or more of EXACTLY: {q.options}. Put a short reason in `answer`."
    if t == "short_answer":
        return "Leave `value` null. `answer` must be one short sentence (max ~20 words)."
    return "Leave `value` null. `answer` is a natural 1-4 sentence reply in the persona's own voice."


def normalise_value(q: QuestionSpec, a: PersonaAnswer) -> Any:
    """Return the typed value or raise AnswerFormatError (triggers a retry with feedback)."""
    v, t = a.value, q.type
    if t in ("open_ended", "short_answer"):
        return None
    if t == "yes_no":
        if isinstance(v, bool):
            return v
        if isinstance(v, str) and v.strip().lower() in ("yes", "no", "true", "false"):
            return v.strip().lower() in ("yes", "true")
        raise AnswerFormatError("yes_no question needs value true/false")
    if t in ("rating", "likert", "numeric"):
        if isinstance(v, bool) or v is None:
            raise AnswerFormatError(f"{t} question needs a numeric value")
        try:
            num = float(v)
        except (TypeError, ValueError):
            raise AnswerFormatError(f"{t} value is not a number: {v!r}")
        if t == "numeric":
            return num
        if num != int(num) or not (q.scale_min <= num <= q.scale_max):
            raise AnswerFormatError(f"value must be an integer between {q.scale_min} and {q.scale_max}, got {v!r}")
        return int(num)
    opts = {o.strip().lower(): o for o in (q.options or [])}
    if t == "single_choice":
        if isinstance(v, list) and len(v) == 1:
            v = v[0]
        if isinstance(v, str) and v.strip().lower() in opts:
            return opts[v.strip().lower()]
        raise AnswerFormatError(f"value must be exactly one of {q.options}")
    if t == "multiple_choice":
        vals = [v] if isinstance(v, str) else v
        if not isinstance(vals, list) or not vals or any(not isinstance(x, str) or x.strip().lower() not in opts for x in vals):
            raise AnswerFormatError(f"value must be a non-empty list drawn from {q.options}")
        return list(dict.fromkeys(opts[x.strip().lower()] for x in vals))
    raise AnswerFormatError(f"unknown question type {t}")


_META = re.compile(r"\b(as an ai|language model|i am an? (ai|bot|llm)|i'?m an? (ai|bot|llm)|synthetic persona|"
                   r"as a persona|in this simulation|i cannot (?:roleplay|pretend)|openrouter|chatgpt)\b", re.I)
_MAX_WORDS = {"open_ended": 150, "short_answer": 30}


@dataclass
class HeuristicReport:
    issues: list[str] = field(default_factory=list)       # hard problems -> regenerate
    warnings: list[str] = field(default_factory=list)


def heuristic_checks(q: QuestionSpec, a: PersonaAnswer, persona_age: int) -> HeuristicReport:
    r = HeuristicReport()
    text = (a.answer or "").strip()
    if len(text) < 2:
        r.issues.append("empty answer")
    if _META.search(text):
        r.issues.append("contains AI/meta language")
    words = len(text.split())
    if words > _MAX_WORDS.get(q.type, 80):
        r.issues.append(f"too verbose ({words} words)")
    # demographic sanity: "N years of experience/working" must fit the persona's age
    for m in re.finditer(r"\b(\d{1,2})\s*(?:\+\s*)?years?\s+(?:of\s+)?(?:experience|working|in (?:my|this)|as a)", text, re.I):
        if int(m.group(1)) > max(persona_age - 15, 0):
            r.issues.append(f"claims {m.group(1)} years of experience, implausible for age {persona_age}")
    return r
