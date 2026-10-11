"""Removes personal data from free-text feedback before it is stored or analyzed."""
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

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


_WORD = re.compile(r"(?<![\w\[])[^\W\d_][\w\-']{2,}(?!\w)", re.UNICODE)

_CYRILLIC_TO_LATIN = str.maketrans({
    "а": "a", "ә": "a", "б": "b", "в": "v", "г": "g", "ғ": "g", "д": "d",
    "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k",
    "қ": "k", "л": "l", "м": "m", "н": "n", "ң": "n", "о": "o", "ө": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ұ": "u", "ү": "u",
    "ф": "f", "х": "h", "һ": "h", "ц": "c", "ч": "ch", "ш": "sh",
    "щ": "sh", "ъ": "", "ы": "y", "і": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
})


def _normalise_name(value: str) -> str:
    """Normalise spelling noise without changing the stored comment.

    Repeated letters are collapsed, so privacy protection still recognises
    variants such as ``Ааайгерым`` or ``Aiiigerim``.  The same normalisation is
    applied to the database name and the submitted token.
    """
    value = value.casefold()
    value = re.sub(r"[^\w]", "", value, flags=re.UNICODE)
    value = re.sub(r"(.)\1+", r"\1", value)
    # University records and comments often mix scripts (Aigerim / Айгерім /
    # Aигерим). A shared Latin comparison key closes that privacy gap.
    return value.translate(_CYRILLIC_TO_LATIN)


def _edit_distance_within(left: str, right: str, limit: int) -> bool:
    """Bounded Levenshtein comparison; exits early when a match is impossible."""
    if abs(len(left) - len(right)) > limit:
        return False
    if left == right:
        return True
    previous = list(range(len(right) + 1))
    for row, char_left in enumerate(left, 1):
        current = [row]
        row_best = current[0]
        for column, char_right in enumerate(right, 1):
            current.append(min(
                current[column - 1] + 1,
                previous[column] + 1,
                previous[column - 1] + (char_left != char_right),
            ))
            row_best = min(row_best, current[-1])
        if row_best > limit:
            return False
        previous = current
    return previous[-1] <= limit


@dataclass(frozen=True)
class KnownNameMatcher:
    """Privacy-first matcher for names that already exist in university data."""

    names: tuple[str, ...]

    def _is_name(self, token: str) -> bool:
        candidate = _normalise_name(token)
        if len(candidate) < 4:
            return False
        for known in self.names:
            # Common Russian/Kazakh inflections may append up to three letters.
            if candidate.startswith(known) and len(candidate) - len(known) <= 3:
                return True
            limit = 1 if max(len(candidate), len(known)) <= 6 else 2
            if _edit_distance_within(candidate, known, limit):
                return True
        return False

    def sub(self, replacement: str, text: str) -> str:
        masked = _WORD.sub(lambda match: replacement if self._is_name(match.group(0)) else match.group(0), text)
        # A first name and surname should appear as one removed item in the receipt.
        return re.sub(r"\[NAME\](?:\s+\[NAME\])+", replacement, masked)


def names_pattern(full_names: Iterable[str]) -> KnownNameMatcher | None:
    """Builds a matcher for people known to the system (e.g. every instructor's first name and surname).

    Source names must be capitalised account-name parts, while submitted text is
    matched case-insensitively and tolerates small spelling noise. Consecutive
    name parts ("Aigerim Nurlanovna") collapse into a single [NAME].
    """
    parts: set[str] = set()
    for full in full_names:
        for word in re.findall(r"[\w\-']+", full or ""):
            if len(word) >= 3 and word.lower() not in _NOT_NAMES and word[0].isupper():
                normalised = _normalise_name(word)
                if len(normalised) >= 4:
                    parts.add(normalised)
    if not parts:
        return None
    return KnownNameMatcher(tuple(sorted(parts, key=len, reverse=True)))


def mask_pii_report(text: str, known_names: KnownNameMatcher | re.Pattern | None = None) -> tuple[str, Counter]:
    """Returns the masked text and how many items of each kind were removed."""
    before = Counter(PLACEHOLDER.findall(text))
    out = text
    for rx, repl in PATTERNS:
        out = rx.sub(repl, out)
    if known_names is not None:
        out = known_names.sub("[NAME]", out)
    after = Counter(PLACEHOLDER.findall(out))
    return out, after - before


def mask_pii(text: str, known_names: KnownNameMatcher | re.Pattern | None = None) -> tuple[str, bool]:
    out, removed = mask_pii_report(text, known_names)
    return out, bool(removed)
