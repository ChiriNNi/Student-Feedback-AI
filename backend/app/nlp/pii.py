"""Removes personal data from free-text feedback before it is stored or analyzed."""
import re

UPPER = "A-ZА-ЯЁӘҒҚҢӨҰҮҺІ"
NAME = rf"[{UPPER}][\w\-']+"

PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"(?<!\w)\+?\d[\d\s\-()]{8,}\d(?!\w)"), "[PHONE]"),
    (re.compile(r"\b\d{9}\b"), "[ID]"),
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


def mask_pii(text: str) -> tuple[str, bool]:
    out = text
    for rx, repl in PATTERNS:
        out = rx.sub(repl, out)
    return out, out != text
