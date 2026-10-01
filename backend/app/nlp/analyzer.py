"""Lightweight multilingual feedback analyzer.

Pipeline for a single comment:
    PII masking -> language detection -> sentence split -> tokenization
    -> lexicon sentiment (negation, intensifiers, contrast) per sentence
    -> topic detection per sentence -> aspect sentiment -> keywords
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from .lexicons import (
    CONTRAST, EXCESS, INTENSIFIERS, LEXICON, NEGATIONS_AFTER, NEGATIONS_BEFORE, STOPWORDS,
)
from .pii import mask_pii

KAZAKH_CHARS = set("әғқңөұүһіӘҒҚҢӨҰҮҺІ")
CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")
TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*|\d+", re.UNICODE)
SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")
CLAUSE_RE = re.compile(
    r",|;|\s[-—]\s|\b(?:but|however|although|though|whereas|while)\b"
    r"|(?<!\w)(?:но|однако|зато|а|бірақ|алайда)(?!\w)",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\[(?:NAME|EMAIL|PHONE|ID)\]")

POS_THRESHOLD = 0.15
NEG_THRESHOLD = -0.15

_SINGLE = {k: v for k, v in LEXICON.items() if " " not in k}
_PHRASES = {k: v for k, v in LEXICON.items() if " " in k}
_MAX_STEM = max(len(k) for k in _SINGLE)


@dataclass
class TopicMatcher:
    name: str
    stems: list[str]
    phrases: list[str] = field(default_factory=list)


@dataclass
class Analysis:
    text: str
    language: str
    sentiment: str
    score: float
    confidence: float
    topics: list[str]
    aspects: dict[str, str]
    keywords: list[str]
    pii_masked: bool


def detect_language(text: str) -> str:
    if any(ch in KAZAKH_CHARS for ch in text):
        return "kk"
    cyr = len(CYRILLIC_RE.findall(text))
    lat = len(re.findall(r"[a-zA-Z]", text))
    return "ru" if cyr > lat else "en"


def tokenize(text: str) -> list[str]:
    return [t.lower().replace("’", "'") for t in TOKEN_RE.findall(text)]


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_RE.split(text) if p and p.strip()]
    return parts or [text.strip()]


def _lex_score(token: str) -> float:
    if token in _SINGLE:
        return _SINGLE[token]
    # longest prefix match for stems >= 4 chars (handles RU/KK inflection)
    for n in range(min(len(token), _MAX_STEM), 3, -1):
        stem = token[:n]
        if stem in _SINGLE and len(stem) >= 4:
            return _SINGLE[stem]
    return 0.0


def _normalize(raw: float, alpha: float = 4.0) -> float:
    return raw / math.sqrt(raw * raw + alpha)


def sentence_sentiment(sentence: str) -> tuple[float, int]:
    """Returns (normalized score in [-1, 1], number of sentiment-bearing words)."""
    # negation scope ends at punctuation: "never covered, very unfair" stays negative
    tokens: list[str] = []
    for chunk in re.split(r"[,;:()]", sentence):
        tokens += tokenize(chunk) + ["<sep>"]
    low = sentence.lower()
    total = 0.0
    hits = 0
    weight = 1.0
    negate_left = 0
    boost = 1.0
    scores: list[float] = []

    excess = False
    for tok in tokens:
        if tok == "<sep>":
            if excess:  # "too many deadlines": no opinion word followed, the excess itself is negative
                total -= 0.6 * weight
                hits += 1
            negate_left, excess = 0, False
            continue
        if tok in CONTRAST:
            # the clause after "but" usually carries the real opinion
            total *= 0.5
            weight = 1.5
            negate_left = 0
            continue
        if tok in NEGATIONS_BEFORE:
            negate_left = 3
            continue
        if tok in NEGATIONS_AFTER and scores:
            # Kazakh: flip the previous sentiment word
            last = scores[-1]
            total -= 2 * last * 0.9
            scores[-1] = -last
            continue
        if tok in INTENSIFIERS:
            boost = INTENSIFIERS[tok]
            continue
        if tok in EXCESS:
            excess = True
            continue

        s = _lex_score(tok)
        if s:
            if excess:
                s, excess = -abs(s) * 1.1, False
            s *= boost * weight
            if negate_left > 0:
                s *= -0.75
            total += s
            scores.append(s)
            hits += 1
            boost = 1.0
        if negate_left > 0:
            negate_left -= 1

    for phrase, s in _PHRASES.items():
        if phrase in low:
            total += s * weight
            hits += 1

    if "!" in sentence and total:
        total *= 1.1
    return _normalize(total), hits


def label_for(score: float) -> str:
    if score >= POS_THRESHOLD:
        return "positive"
    if score <= NEG_THRESHOLD:
        return "negative"
    return "neutral"


def _match_topics(tokens: list[str], low_text: str, matchers: list[TopicMatcher]) -> Counter:
    found: Counter = Counter()
    for m in matchers:
        n = 0
        for tok in tokens:
            for stem in m.stems:
                if (len(stem) < 4 and tok == stem) or (len(stem) >= 4 and tok.startswith(stem)):
                    n += 1
                    break
        for ph in m.phrases:
            if ph in low_text:
                n += 1
        if n:
            found[m.name] += n
    return found


def build_matchers(categories: list[dict]) -> list[TopicMatcher]:
    out = []
    for c in categories:
        kws = [k.lower().strip() for k in c.get("keywords", []) if k and k.strip()]
        out.append(TopicMatcher(
            name=c["name"],
            stems=[k for k in kws if " " not in k],
            phrases=[k for k in kws if " " in k],
        ))
    return out


def extract_keywords(tokens: list[str], limit: int = 8) -> list[str]:
    words = [t for t in tokens if len(t) >= 4 and t not in STOPWORDS and not t.isdigit()]
    return [w for w, _ in Counter(words).most_common(limit)]


def analyze(text: str, matchers: list[TopicMatcher], rating: int | None = None) -> Analysis:
    masked, had_pii = mask_pii(text)
    lang = detect_language(masked)
    sentences = split_sentences(masked)

    sent_scores: list[tuple[float, int]] = []
    topic_hits: Counter = Counter()
    aspect_acc: dict[str, list[float]] = {}

    for s in sentences:
        score, hits = sentence_sentiment(s)
        sent_scores.append((score, hits))
        clean = PLACEHOLDER_RE.sub(" ", s)
        # aspects are scored per clause so "good teacher, but heavy workload" splits correctly
        for clause in [c for c in CLAUSE_RE.split(clean) if c and c.strip()]:
            t = _match_topics(tokenize(clause), clause.lower(), matchers)
            if not t:
                continue
            c_score, c_hits = sentence_sentiment(clause)
            topic_hits.update(t)
            for name in t:
                aspect_acc.setdefault(name, []).append(c_score if c_hits else score)

    weighted = [sc * max(h, 1) for sc, h in sent_scores]
    total_hits = sum(max(h, 1) for _, h in sent_scores)
    text_score = sum(weighted) / total_hits if total_hits else 0.0
    any_hits = sum(h for _, h in sent_scores)

    # Blend with the numeric rating when present (1..5 -> -1..1)
    if rating:
        r = (max(1, min(5, rating)) - 3) / 2
        score = 0.7 * text_score + 0.3 * r if any_hits else 0.35 * text_score + 0.65 * r
    else:
        score = text_score
    score = max(-1.0, min(1.0, score))

    confidence = min(0.99, 0.45 + abs(score) * 0.5 + min(any_hits, 6) * 0.03)
    aspects = {k: label_for(sum(v) / len(v)) for k, v in aspect_acc.items()}
    topics = [name for name, _ in topic_hits.most_common()]

    return Analysis(
        text=masked,
        language=lang,
        sentiment=label_for(score),
        score=round(score, 4),
        confidence=round(confidence, 3),
        topics=topics,
        aspects=aspects,
        keywords=extract_keywords(tokenize(PLACEHOLDER_RE.sub(" ", masked))),
        pii_masked=had_pii,
    )
