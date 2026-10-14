"""Conservative local privacy checks and code-owned messages."""

from __future__ import annotations

import re


PII_MESSAGE = (
    "Please remove personal details such as an email address, telephone number, "
    "or student ID, then submit your economics question again. No API request was sent."
)
INSUFFICIENT_MESSAGE = (
    "The selected textbook passages do not provide enough evidence to answer this question. "
    "Try a question about demand, supply, market equilibrium, or elasticity, "
    "or select all available chapters."
)
CONNECTION_MESSAGE = (
    "The model connection failed. Check your API key, endpoint, and model, then try again. "
    "Source search is still available without an API key."
)
PROTOCOL_MESSAGE = (
    "The model returned an invalid or unverifiable response. No answer is shown. "
    "Please try again or use Source search to inspect the textbook."
)
REFUSAL_MESSAGES = {
    "advice": "I can explain textbook economics concepts, but I cannot recommend investments or make financial decisions for you.",
    "prediction": "I can explain textbook economics concepts, but I cannot predict market prices or future market outcomes.",
    "assignment": "I can explain textbook concepts, but I cannot write or grade assessed work, or check its solution steps.",
    "off_topic": "This assistant supports English-language economics learning questions. Please ask about an economics concept.",
}
_EMAIL = re.compile(
    r"(?<![\w.+-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?\.[A-Z]{2,}"
    # A final sentence period is allowed; an unfinished domain suffix is not.
    r"(?![\w-]|\.[\w-])", re.I,
)
_STUDENT_ID = re.compile(
    r"\b(?:student\s*(?:id|number|no\.?|identification)|university\s*id|sid)"
    r"\s*(?:(?:is|number)\s*)?[:#=\-]?\s*[A-Z0-9][A-Z0-9-]{5,19}\b", re.I,
)
_LABELED_PHONE = re.compile(
    r"\b(?:phone|telephone|mobile|tel|contact\s+number)\s*(?:number|no\.?)?"
    r"\s*(?:is\s*)?[:#=]?\s*(\+?[\d(][\d ()\-]{5,25}\d)", re.I,
)
_INTERNATIONAL_PHONE = re.compile(r"(?<![\w\d])\+\d[\d ()\-]{6,23}\d(?!\w)")
_SEPARATED_PHONE = re.compile(r"(?<!\d)(?:\(\d{3}\)|\d{3})[ -]\d{3}[ -]\d{4}(?!\d)")
_CHINA_MOBILE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def contains_personal_data(text: str) -> bool:
    """Spot obvious synthetic/real contact details before any network operation.

    Arbitrary numbers are deliberately not considered IDs or telephones; ordinary
    prices, quantities, years, percentages, and elasticity calculations remain usable.
    This is a basic pattern check, not a guarantee that all personal data is detected.
    """
    if _EMAIL.search(text) or _STUDENT_ID.search(text):
        return True
    if _SEPARATED_PHONE.search(text) or _CHINA_MOBILE.search(text):
        return True
    for pattern in (_LABELED_PHONE, _INTERNATIONAL_PHONE):
        for match in pattern.finditer(text):
            candidate = match.group(1) if pattern is _LABELED_PHONE else match.group(0)
            if 8 <= len(re.sub(r"\D", "", candidate)) <= 15:
                return True
    return False


def is_english_input(text: str) -> bool:
    """Reject obvious non-Latin script; allow English punctuation and math symbols."""
    if not re.search(r"[A-Za-z]", text):
        return False
    return not any(character.isalpha() and ord(character) > 0x024F for character in text)
