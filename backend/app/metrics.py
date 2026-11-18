"""Shared aggregates for persisted feedback and its analysis."""
from collections import Counter

from .models import SENTIMENTS


def _response_rating(row: dict) -> float | None:
    ratings = row.get("ratings")
    answers = [value for value in ratings.values() if type(value) is int and 1 <= value <= 5] if isinstance(ratings, dict) else []
    if answers:
        return sum(answers) / len(answers)
    rating = row.get("rating")
    return rating if rating is not None and 1 <= rating <= 5 else None


def feedback_metrics(rows: list[dict]) -> dict:
    counts = Counter(row["sentiment"] for row in rows
                     if (row.get("confidence") or 0) > 0 or row.get("is_corrected"))
    analyzed = sum(counts[tone] for tone in SENTIMENTS)
    shares = {tone: counts[tone] / analyzed if analyzed else 0
              for tone in SENTIMENTS}
    ratings = [rating for row in rows if (rating := _response_rating(row)) is not None]
    return {
        "total": len(rows), "analyzed": analyzed, "rated": len(ratings),
        **{tone: counts[tone] for tone in SENTIMENTS},
        **{f"{tone}_share": shares[tone] for tone in SENTIMENTS},
        "satisfaction_index": (counts["positive"] - counts["negative"]) * 100 / analyzed if analyzed else 0,
        "avg_rating": sum(ratings) / len(ratings) if ratings else None,
    }
