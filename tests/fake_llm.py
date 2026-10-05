"""Deterministic stand-in for llm.ainvoke_structured. Answers DEPEND on persona text (so personas differ and tests mean something)."""
import re

from llm import LLMError
from schemas_m3 import (AgreementOut, ConsistencyIssue, ConsistencyResult, ContradictionOut, EvidenceRef, InsightLLMOut, MemoryUpdate,
                        OutlierOut, PersonaAnswer, RealismResult, StanceOut, ThemeOut, TrendOut, UsageEval, UsageFactor, ValidationResult)


def leaning(text: str) -> int:
    t = text.lower()
    s = sum(w in t for w in ("convenien", "time-poor", "busy", "tech savviness: high", "early adopter"))
    s -= sum(w in t for w in ("price-sensitive", "skeptical", "tech savviness: low", "risk averse", "distrust"))
    return max(-1, min(1, s))


class FakeLLM:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.fail_if = None             # callable(schema_name, inputs) -> Exception | None
        self.bad_value_for = None       # substring of persona text -> always return invalid typed value
        self.inconsistent_for = None    # substring of persona text -> validator always says inconsistent
        self.extra_theme_id = "ghost-persona"

    def count(self, name):
        return sum(1 for n, _ in self.calls if n == name)

    async def __call__(self, prompt, schema, inputs, temperature=0.7, label="x"):
        name = schema.__name__
        self.calls.append((name, inputs))
        if self.fail_if and (exc := self.fail_if(name, inputs)):
            raise exc
        return getattr(self, f"_{name}")(inputs)

    # ---- persona answer ----
    def _PersonaAnswer(self, i):
        persona, q, qt = i["persona"], i["question"], i["qtype"]
        lean = leaning(persona)
        pricey = "price" in persona.lower() or "budget" in persona.lower()
        mem = i["memories"].lower()
        text = ("Price matters a lot to me, I always compare fees." if pricey
                else "Convenience matters most; I'd happily pay for something that saves time." if lean > 0
                else "I'm not sure this is for me, I prefer what I already know.")
        if "switch" in q.lower() and "price" in mem:
            text = "A better price would make me switch, that is what I care about most."
        if "price" in q.lower() and pricey:
            text = "Yes, price is one of my biggest concerns."
        value = None
        if self.bad_value_for and self.bad_value_for in persona:
            value = 99 if qt in ("rating", "likert") else "garbage"
        elif qt == "yes_no":
            value = lean >= 0
        elif qt in ("rating", "likert"):
            value = max(1, min(5, 3 + lean))
        elif qt == "numeric":
            value = 10.0 + 5 * lean + (0 if pricey else 5)
        elif qt == "single_choice":
            opts = re.findall(r"'([^']+)'", i["format_instructions"])
            value = opts[0] if lean > 0 else opts[-1]
        elif qt == "multiple_choice":
            value = re.findall(r"'([^']+)'", i["format_instructions"])[:1]
        mu = []
        if pricey and ("price" in q.lower() or qt != "open_ended"):
            mu.append(MemoryUpdate(layer="derived", content="Price is one of my biggest concerns when choosing products", importance=0.9))
        return PersonaAnswer(answer=text, value=value, sentiment="positive" if lean > 0 else "negative" if lean < 0 else "neutral",
                             confidence=0.8, memory_updates=mu)

    # ---- validation ----
    def _ValidationResult(self, i):
        bad = self.inconsistent_for and self.inconsistent_for in i["persona"]
        issues = [ConsistencyIssue(type="behavioral_contradiction", description="conflicts with persona's price-sensitive behaviour")] if bad else []
        return ValidationResult(
            consistency=ConsistencyResult(consistent=not bad, confidence=0.87 if bad else 0.91, issues=issues),
            realism=RealismResult(relevant=True, answers_the_question=True, grounded_in_persona=True, too_generic=False,
                                  plausible_human=True, too_verbose=False, meta_language=False, score=0.8))

    # ---- insights ----
    def _InsightLLMOut(self, i):
        rows = [ln.split(" | ", 3) for ln in i["items"].splitlines() if ln.count(" | ") >= 3]
        price = sorted({r[0] for r in rows if "price" in r[3].lower()})
        conv = sorted({r[0] for r in rows if "convenien" in r[3].lower()})
        pos = sorted({r[0] for r in rows if r[2] == "positive"})
        neg = sorted({r[0] for r in rows if r[2] == "negative"})
        key = lambda pid: next(r[1] for r in rows if r[0] == pid)
        themes = []
        if price:
            themes.append(ThemeOut(name="Price sensitivity", sentiment="negative", persona_ids=price + [self.extra_theme_id],
                                   evidence=[EvidenceRef(persona_id=price[0], question_key=key(price[0]))]))
        if conv:
            themes.append(ThemeOut(name="Convenience", sentiment="positive", persona_ids=conv))
        return InsightLLMOut(themes=themes,
                             agreement_patterns=[AgreementOut(statement="price is important", persona_ids=price)] if price else [],
                             behavioral_trends=[TrendOut(trend="Time-poor personas prioritise convenience", segments=["working_professionals"], persona_ids=conv)],
                             contradictions=[ContradictionOut(topic="Willingness to adopt", positions=[
                                 StanceOut(stance="positive", persona_ids=pos), StanceOut(stance="negative", persona_ids=neg)])] if pos and neg else [],
                             outliers=[OutlierOut(persona_id=neg[0], reason="only strongly negative persona")] if neg else [])

    # ---- usage ----
    def _UsageEval(self, i):
        lean = leaning(i["persona"])
        occ = re.search(r"Occupation: (.*)", i["persona"]).group(1)
        score = 50 + 30 * lean + (5 if i["evidence"] != "(none)" else 0)
        return UsageEval(score=score, confidence=0.8,
                         reasoning=f"As a {occ}, the product {'reduces effort' if lean > 0 else 'does not fit their habits' if lean < 0 else 'is a mixed fit'}.",
                         factors=[UsageFactor(factor="fit with habits", impact="positive" if lean >= 0 else "negative", weight=0.7)])


def timeout(msg="timeout"):
    return LLMError(msg, "timeout")
