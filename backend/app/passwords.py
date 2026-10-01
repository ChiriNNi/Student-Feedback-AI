"""Password policy shared by registration, admin user management and password change.

Beyond length and character classes it rejects passwords that are easy to guess:
well-known common passwords (including leetspeak and "word + digits" variants),
keyboard/alphabet sequences, highly repetitive strings, and passwords that
contain the account's own name, email or student ID.
"""
import re

MIN_LENGTH = 8

# Base words that make a password predictable when followed only by digits/symbols
# ("password1", "Qwerty2026!", "admin123", "student2025"...).
COMMON_BASES = {
    "password", "passwd", "passw", "pass", "pwd", "qwerty", "qwertyuiop", "asdf", "asdfgh", "zxcvbn",
    "admin", "administrator", "root", "user", "login", "welcome", "letmein", "iloveyou", "love",
    "hello", "secret", "master", "monkey", "dragon", "football", "baseball", "soccer", "sunshine",
    "princess", "superman", "batman", "shadow", "michael", "charlie", "test", "guest", "default",
    "student", "teacher", "faculty", "manager", "university", "college", "school", "sdu", "abc",
    "qazwsx", "trustno", "freedom", "whatever", "starwars", "pokemon", "google", "computer",
    "kazakhstan", "almaty", "astana", "parol", "privet",
}

# Whole passwords seen in breach top lists that would otherwise pass the rules.
COMMON_PASSWORDS = {
    "1q2w3e4r", "1q2w3e4r5t", "q1w2e3r4", "q1w2e3r4t5", "1qaz2wsx", "zaq12wsx", "a1b2c3d4",
    "1a2b3c4d", "abcd1234", "abc12345", "aa123456", "a1234567", "1234567a", "12345678a",
    "123456789a", "qwer1234", "1234qwer", "asdf1234", "zxcv1234", "pass1234", "test1234",
}

SEQUENCES = (
    "abcdefghijklmnopqrstuvwxyz", "0123456789", "1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "qazwsxedc", "1qaz2wsx3edc",
)
LEET = str.maketrans({"@": "a", "4": "a", "0": "o", "1": "i", "!": "i", "3": "e", "$": "s", "5": "s", "7": "t"})


def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", s)


def _is_sequence(part: str) -> bool:
    """True for runs like 'abcd', '4321', 'qwerty' or a single repeated character."""
    if len(part) < 3:
        return len(set(part)) <= 1
    if len(set(part)) == 1:
        return True
    return any(part in seq or part in seq[::-1] for seq in SEQUENCES)


def password_problem(password: str, *, name: str | None = None, email: str | None = None,
                     student_id: str | None = None) -> str | None:
    """Return a human-readable reason the password is unacceptable, or None if it's fine."""
    if len(password) < MIN_LENGTH:
        return f"Password must be at least {MIN_LENGTH} characters."
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        return "Password must contain both letters and digits."

    low = password.lower()
    core = re.sub(r"[^a-z0-9]", "", low)
    if low in COMMON_PASSWORDS or core in COMMON_PASSWORDS:
        return "This password is too common. Choose something less predictable."

    # "password1", "p@ssw0rd!", "Qwerty2026" — a common word plus digits/symbols.
    trimmed = re.sub(r"[^a-z]+$", "", low)
    for candidate in {_letters(low), _letters(low.translate(LEET)), _letters(trimmed.translate(LEET))}:
        if candidate in COMMON_BASES:
            return "This password is too common. Choose something less predictable."

    # "aaaa1111", "ab12ab12ab12": very few distinct characters or one short unit repeated.
    if len(set(low)) <= 3 or re.fullmatch(r"(.{1,4})\1+", core):
        return "Password is too repetitive."

    # "abcd1234", "qwerty123", "zxcv0987": every letters/digits chunk is a sequence.
    chunks = re.findall(r"[a-z]+|[0-9]+", core)
    if chunks and all(_is_sequence(c) for c in chunks):
        return "Password must not be a keyboard or alphabet sequence."

    personal = []
    if student_id:
        personal.append(student_id.strip())
    if email:
        local = email.strip().lower().split("@")[0]
        personal.append(local)
        personal += re.split(r"[._\-+]", local)
    if name:
        personal += name.lower().split()
    for item in personal:
        if len(item) >= 4 and item.lower() in low:
            return "Password must not contain your name, email or student ID."
    return None
