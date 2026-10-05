"""Deterministic persona -> segment classifier (used to aggregate scores/insights by segment).
Rule-based on purpose: transparent and reproducible. Can be overridden when personas are created."""
import re

_RULES = [
    ("retired", r"\bretire|pension|senior citizen|grandparent"),
    ("students", r"\bstudent|undergrad|b\.?tech|college|university|school|intern\b"),
    ("parents", r"\bparent|mother|father|\bmom\b|\bdad\b|homemaker|stay-at-home|raising (kids|children)"),
    ("freelancers", r"freelanc|self-employed|gig worker|independent contractor|consultant"),
    ("working_professionals", r"engineer|manager|analyst|developer|executive|professional|accountant|nurse|teacher|designer|"
                              r"officer|lawyer|doctor|marketing|sales|employee|corporate"),
]


def classify_segment(occupation: str, background: str = "") -> str:
    text = f"{occupation} {background}".lower()
    # occupation takes priority over background: check occupation alone first
    for source in (occupation.lower(), text):
        for name, pattern in _RULES:
            if re.search(pattern, source):
                return name
    return "other"
