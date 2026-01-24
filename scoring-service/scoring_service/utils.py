import re
from typing import Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-() ]{7,}\d)\b")
CARD_RE = re.compile(r"\b\d{13,19}\b")

IMAGE_RE = re.compile(
    r"^(?:[a-z0-9]+(?:(?:[._-][a-z0-9]+)+)?/)*"
    r"[a-z0-9]+(?:(?:[._-][a-z0-9]+)+)?"
    r"(?:[:][a-zA-Z0-9_.-]+)?"
    r"(?:@sha256:[a-f0-9]{64})?$"
)


def redact_pii(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    redacted = EMAIL_RE.sub("[redacted-email]", text)
    redacted = PHONE_RE.sub("[redacted-phone]", redacted)
    redacted = CARD_RE.sub("[redacted-card]", redacted)
    return redacted


def is_valid_container_image(image: str) -> bool:
    return bool(IMAGE_RE.match(image))
