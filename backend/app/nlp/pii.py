"""Removes personal data from free-text feedback before it is stored or analyzed."""
import re
from collections import Counter
from collections.abc import Iterable

UPPER = "A-ZА-ЯЁӘҒҚҢӨҰҮҺІ"
NAME = rf"[{UPPER}][\w\-']+"


def _phone(m: re.Match) -> str:
    # Real phone numbers have 10-15 digits; this keeps "2025 2026" or "1 2 3 4 5" intact.
    digits = sum(ch.isdigit() for ch in m.group(0))
    return "[PHONE]" if 10 <= digits <= 15 else m.group(0)


PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    # Telegram / Instagram handles: "@aigerim_b"
    (re.compile(r"(?<![\w.])@[A-Za-z][\w.]{3,31}\b"), "[CONTACT]"),
    # 12-digit Kazakh IIN and 9-digit university IDs, before phones swallow them
    (re.compile(r"\b\d{12}\b"), "[ID]"),
    (re.compile(r"\b\d{9}\b"), "[ID]"),
    (re.compile(r"(?<!\w)\+?\d[\d\s\-()]{8,}\d(?!\w)"), _phone),
    # "teacher John Smith", "преподаватель Иванов", "мұғалім Асқаров"
    (re.compile(
        rf"((?i:\b(?:teacher|professor|prof\.?|mr\.?|mrs\.?|ms\.?|dr\.?|instructor|lecturer|tutor|"
        rf"преподавател\w*|учител\w*|профессор\w*|лектор\w*|мұғалім\w*|оқытушы\w*|ұстаз\w*))\s+)"
        rf"{NAME}(?:\s+{NAME})?"
    ), r"\1[NAME]"),
    # Kazakh honorifics after the name: "Айгүл апай", "Ерлан ағай"
    (re.compile(rf"\b{NAME}(\s+(?:апай|ағай|мырза|ханым))\b"), r"[NAME]\1"),
    # Self-identification
    (re.compile(rf"((?i:my name is|меня зовут|я\s*[-—]|менің атым)\s+){NAME}(?:\s+{NAME})?"), r"\1[NAME]"),
]

PLACEHOLDER = re.compile(r"\[(EMAIL|CONTACT|ID|PHONE|NAME)\]")

# Words that appear in account names but are not personal names ("Demo Student", "System Administrator").
_NOT_NAMES = {
    "demo", "test", "student", "faculty", "manager", "admin", "administrator", "system", "user",
    "quality", "assurance", "office", "department", "university", "dr", "prof", "mr", "mrs", "ms",
}


def names_pattern(full_names: Iterable[str]) -> re.Pattern | None:
    """Builds a matcher for people known to the system (e.g. every instructor's first name and surname).

    Matching is case-sensitive on the capitalised form, so the surname "Mark" doesn't eat the word "mark".
    Consecutive name parts ("Aigerim Nurlanovna") collapse into a single [NAME].
    """
    parts = set()
    for full in full_names:
        for word in re.findall(r"[\w\-']+", full or ""):
            if len(word) >= 3 and word.lower() not in _NOT_NAMES and word[0].isupper():
                parts.add(word)
    if not parts:
        return None
    alt = "|".join(re.escape(p) for p in sorted(parts, key=len, reverse=True))
    # Allow a short inflected ending: "Нурлановной", "Bolat's"
    token = rf"(?:{alt})(?:'s|[а-яәғқңөұүһі]{{0,3}})?"
    return re.compile(rf"(?<![\w\[]){token}(?:\s+{token})*(?!\w)")


def mask_pii_report(text: str, known_names: re.Pattern | None = None) -> tuple[str, Counter]:
    """Returns the masked text and how many items of each kind were removed."""
    before = Counter(PLACEHOLDER.findall(text))
    out = text
    for rx, repl in PATTERNS:
        out = rx.sub(repl, out)
    if known_names is not None:
        out = known_names.sub("[NAME]", out)
    after = Counter(PLACEHOLDER.findall(out))
    return out, after - before


def mask_pii(text: str, known_names: re.Pattern | None = None) -> tuple[str, bool]:
    out, removed = mask_pii_report(text, known_names)
    return out, bool(removed)
