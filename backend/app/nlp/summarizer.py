"""Feedback summarization.

`local_summary` is fully offline: aspect statistics + TF-IDF centrality for
representative comments + clustered improvement suggestions.
`llm_summary` optionally rewrites the narrative with Claude when
ANTHROPIC_API_KEY is configured; it always falls back to the local result.
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter, defaultdict

from ..config import settings
from .analyzer import split_sentences, tokenize
from .lexicons import STOPWORDS, SUGGESTION_MARKERS

log = logging.getLogger("pulse.summary")


def _terms(text: str) -> list[str]:
    return [t for t in tokenize(text) if len(t) > 2 and t not in STOPWORDS and not t.isdigit()]


def _tfidf_rank(texts: list[str], top: int) -> list[int]:
    """Indices of the texts closest to the centroid of the group (most 'typical')."""
    if not texts:
        return []
    docs = [Counter(_terms(t)) for t in texts]
    df = Counter()
    for d in docs:
        df.update(d.keys())
    n = len(docs)
    vecs = []
    for d in docs:
        v = {w: (c / max(1, sum(d.values()))) * math.log((1 + n) / (1 + df[w]) + 1) for w, c in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    centroid: dict[str, float] = defaultdict(float)
    for v in vecs:
        for w, x in v.items():
            centroid[w] += x / n
    scores = []
    for i, v in enumerate(vecs):
        sim = sum(x * centroid.get(w, 0.0) for w, x in v.items())
        length_bonus = min(len(texts[i]), 220) / 220 * 0.15  # prefer informative comments
        scores.append((sim + length_bonus, i))
    scores.sort(reverse=True)
    seen: list[set] = []
    picked = []
    for _, i in scores:
        s = set(_terms(texts[i]))
        if any(len(s & o) / max(1, len(s | o)) > 0.6 for o in seen):
            continue
        seen.append(s)
        picked.append(i)
        if len(picked) >= top:
            break
    return picked


def _suggestions(rows: list[dict], limit: int = 6) -> list[dict]:
    cands: list[tuple[str, set]] = []
    for r in rows:
        for s in split_sentences(r["text"]):
            low = s.lower()
            if any(m in low for m in SUGGESTION_MARKERS) and 12 <= len(s) <= 300:
                cands.append((s.strip(), set(_terms(s))))
    clusters: list[dict] = []
    for text, terms in cands:
        for c in clusters:
            if terms and len(terms & c["terms"]) / max(1, len(terms | c["terms"])) >= 0.4:
                c["count"] += 1
                c["terms"] |= terms
                break
        else:
            clusters.append({"text": text, "terms": terms, "count": 1})
    clusters.sort(key=lambda c: c["count"], reverse=True)
    return [{"text": c["text"], "mentions": c["count"]} for c in clusters[:limit]]


def aspect_stats(rows: list[dict]) -> list[dict]:
    stats: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        for topic, label in (r.get("aspects") or {}).items():
            stats[topic][label] += 1
    out = []
    for topic, c in stats.items():
        total = sum(c.values())
        out.append({
            "topic": topic,
            "total": total,
            "positive": c["positive"],
            "neutral": c["neutral"],
            "negative": c["negative"],
            "positive_share": round(c["positive"] / total, 3),
            "negative_share": round(c["negative"] / total, 3),
        })
    out.sort(key=lambda x: x["total"], reverse=True)
    return out


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def local_summary(rows: list[dict], scope_label: str = "the selected scope") -> dict:
    n = len(rows)
    if not n:
        return {
            "source": "local", "total": 0,
            "overview": "There is no feedback for this selection yet.",
            "strengths": [], "problems": [], "suggestions": [], "aspects": [], "representative": {},
        }

    sent = Counter(r["sentiment"] for r in rows)
    pos, neg = sent["positive"] / n, sent["negative"] / n
    ratings = [r["rating"] for r in rows if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    aspects = aspect_stats(rows)

    min_n = max(3, round(n * 0.03))
    strong = sorted([a for a in aspects if a["total"] >= min_n and a["positive_share"] >= 0.5],
                    key=lambda a: (a["positive_share"], a["total"]), reverse=True)[:3]
    weak = sorted([a for a in aspects if a["total"] >= min_n and a["negative_share"] >= 0.3],
                  key=lambda a: a["negative"] * a["negative_share"], reverse=True)[:3]

    def examples(topic: str, label: str, k: int = 3) -> list[str]:
        pool = [r["text"] for r in rows if (r.get("aspects") or {}).get(topic) == label]
        return [pool[i] for i in _tfidf_rank(pool, k)]

    strengths = [{
        "topic": a["topic"],
        "detail": f"{_pct(a['positive_share'])} of {a['total']} mentions are positive.",
        "examples": examples(a["topic"], "positive", 2),
    } for a in strong]
    problems = [{
        "topic": a["topic"],
        "detail": f"{_pct(a['negative_share'])} of {a['total']} mentions are negative.",
        "examples": examples(a["topic"], "negative", 2),
    } for a in weak]

    mood = "mostly positive" if pos - neg > 0.25 else "mostly negative" if neg - pos > 0.15 else "mixed"
    parts = [f"Based on {n} responses for {scope_label}, overall sentiment is {mood} "
             f"({_pct(pos)} positive, {_pct(neg)} negative)."]
    if avg_rating:
        parts.append(f"The average rating is {avg_rating}/5.")
    if strong:
        parts.append("Students most appreciate " + _join([s["topic"].lower() for s in strong]) + ".")
    if weak:
        parts.append("The most common concerns relate to " + _join([
            f"{w['topic'].lower()} ({_pct(w['negative_share'])} negative)" for w in weak]) + ".")
    if not weak:
        parts.append("No topic stands out as a significant problem.")

    representative = {}
    for a in aspects[:6]:
        pool = [r["text"] for r in rows if a["topic"] in (r.get("aspects") or {})]
        representative[a["topic"]] = [pool[i] for i in _tfidf_rank(pool, 3)]

    return {
        "source": "local",
        "total": n,
        "avg_rating": avg_rating,
        "sentiment": {"positive": sent["positive"], "neutral": sent["neutral"], "negative": sent["negative"]},
        "overview": " ".join(parts),
        "strengths": strengths,
        "problems": problems,
        "suggestions": _suggestions(rows),
        "aspects": aspects,
        "representative": representative,
    }


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


LLM_SYSTEM = (
    "You analyze anonymized university student feedback for academic management. "
    "Comments may be in English, Russian or Kazakh; always answer in English. "
    "Be specific and evidence-based, do not invent facts that are not supported by the comments, "
    "and never try to identify individual students. "
    "Reply with a single JSON object and nothing else, using exactly these keys: "
    '"overview" (3-5 sentence string), '
    '"strengths" (array of {"topic": string, "detail": string}), '
    '"problems" (array of {"topic": string, "detail": string}), '
    '"suggestions" (array of {"text": string}) - concrete, actionable improvement recommendations.'
)


def llm_available() -> bool:
    return bool(settings.anthropic_api_key)


def llm_summary(rows: list[dict], base: dict, scope_label: str) -> dict:
    """Enhance the local summary with Claude. Returns `base` unchanged on any failure."""
    if not llm_available() or not rows:
        return base
    try:
        import anthropic

        # Keep the request bounded: most typical comments first, per sentiment group
        sample: list[str] = []
        for label in ("negative", "positive", "neutral"):
            pool = [r["text"] for r in rows if r["sentiment"] == label]
            sample += [pool[i] for i in _tfidf_rank(pool, 80)]
        stats = {k: base.get(k) for k in ("total", "avg_rating", "sentiment")}
        stats["aspects"] = base.get("aspects", [])[:10]
        user_msg = (
            f"Scope: {scope_label}\n"
            f"Statistics (computed over all {len(rows)} responses): {json.dumps(stats, ensure_ascii=False)}\n\n"
            f"A representative sample of {len(sample)} of the {len(rows)} comments follows, one per line:\n"
            + "\n".join(f"- {s[:600]}" for s in sample)
        )

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=90.0)
        kwargs = dict(
            model=settings.llm_model,
            max_tokens=4000,
            system=LLM_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        try:
            resp = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        except TypeError:  # older SDK without the fallbacks parameter
            resp = client.messages.create(**kwargs)

        if resp.stop_reason == "refusal":
            return base
        text = "".join(b.text for b in resp.content if b.type == "text")
        match = re.search(r"\{.*\}", text, re.S)
        data = json.loads(match.group(0) if match else text)

        merged = dict(base)
        merged["source"] = "llm"
        merged["model"] = settings.llm_model
        merged["overview"] = str(data.get("overview") or base["overview"])
        # Keep local evidence (examples) attached to matching topics
        ex_by_topic = {s["topic"]: s.get("examples", []) for s in base["strengths"] + base["problems"]}
        for key in ("strengths", "problems"):
            items = data.get(key) or []
            if items:
                merged[key] = [{
                    "topic": str(i.get("topic", "")),
                    "detail": str(i.get("detail", "")),
                    "examples": ex_by_topic.get(str(i.get("topic", "")), []),
                } for i in items if isinstance(i, dict)]
        if data.get("suggestions"):
            merged["suggestions"] = [
                {"text": str(s.get("text") if isinstance(s, dict) else s), "mentions": None}
                for s in data["suggestions"]
            ]
        return merged
    except Exception as exc:  # network, auth, parsing... never break the dashboard
        log.warning("LLM summary failed, using local summary: %s", exc)
        out = dict(base)
        out["llm_error"] = "AI service unavailable - showing the built-in summary."
        return out
