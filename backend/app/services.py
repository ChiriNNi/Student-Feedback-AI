"""Shared domain logic: semester ordering, analysis, role scoping, alerts."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Alert, Course, Department, Feedback, Service, TopicCategory, User
from .nlp.analyzer import analyze, build_matchers

# ---------------------------------------------------------------- semesters

_TERM_ORDER = {"spring": 0, "summer": 1, "fall": 2, "autumn": 2}


def semester_key(sem: str) -> tuple[int, int]:
    m = re.match(r"\s*([A-Za-z]+)\s+(\d{4})", sem or "")
    if not m:
        return (0, 0)
    return int(m.group(2)), _TERM_ORDER.get(m.group(1).lower(), 0)


def sort_semesters(items) -> list[str]:
    return sorted(set(items), key=semester_key)


# ---------------------------------------------------------------- analysis

_matchers_cache: dict = {"items": None}


def invalidate_topics() -> None:
    _matchers_cache["items"] = None


def get_matchers(db: Session):
    if _matchers_cache["items"] is None:
        cats = db.scalars(select(TopicCategory).where(TopicCategory.is_active.is_(True))).all()
        _matchers_cache["items"] = build_matchers([{"name": c.name, "keywords": c.keywords} for c in cats])
    return _matchers_cache["items"]


def analyze_into(fb: Feedback, raw_text: str, matchers) -> Feedback:
    a = analyze(raw_text, matchers, fb.rating)
    fb.text = a.text
    fb.language = a.language
    fb.sentiment = a.sentiment
    fb.sentiment_score = a.score
    fb.confidence = a.confidence
    fb.topics = a.topics
    fb.aspects = a.aspects
    fb.keywords = a.keywords
    fb.pii_masked = a.pii_masked
    return fb


# ---------------------------------------------------------------- scoping


@dataclass
class Filters:
    semester: str | None = None
    department_id: int | None = None
    course_id: int | None = None
    service_id: int | None = None
    kind: str | None = None
    sentiment: str | None = None
    topic: str | None = None
    language: str | None = None
    q: str | None = None
    survey_id: int | None = None


def scope_query(stmt: Select, user: User) -> Select:
    """Restrict a Feedback select to what the user's role may see."""
    if user.role == "admin":
        return stmt
    if user.role == "manager":
        if user.department_id:
            # department managers see their department's courses plus university services
            return stmt.where(or_(Feedback.department_id == user.department_id, Feedback.kind == "service"))
        return stmt
    if user.role == "faculty":
        own = select(Course.id).where(Course.instructor_id == user.id)
        return stmt.where(Feedback.course_id.in_(own))
    return stmt.where(Feedback.id < 0)  # students never read feedback


def apply_filters(stmt: Select, f: Filters) -> Select:
    if f.semester:
        stmt = stmt.where(Feedback.semester == f.semester)
    if f.department_id:
        stmt = stmt.where(Feedback.department_id == f.department_id)
    if f.course_id:
        stmt = stmt.where(Feedback.course_id == f.course_id)
    if f.service_id:
        stmt = stmt.where(Feedback.service_id == f.service_id)
    if f.kind:
        stmt = stmt.where(Feedback.kind == f.kind)
    if f.sentiment:
        stmt = stmt.where(Feedback.sentiment == f.sentiment)
    if f.language:
        stmt = stmt.where(Feedback.language == f.language)
    if f.survey_id:
        stmt = stmt.where(Feedback.survey_id == f.survey_id)
    if f.q:
        stmt = stmt.where(Feedback.text.ilike(f"%{f.q.strip()}%"))
    return stmt


def feedback_rows(db: Session, user: User, f: Filters, limit: int | None = None) -> list[dict]:
    """Light-weight dict rows for analytics (topic filter applied in Python because topics is JSON)."""
    stmt = select(
        Feedback.id, Feedback.text, Feedback.sentiment, Feedback.sentiment_score, Feedback.topics,
        Feedback.aspects, Feedback.keywords, Feedback.rating, Feedback.semester, Feedback.kind,
        Feedback.course_id, Feedback.service_id, Feedback.department_id, Feedback.language,
    )
    stmt = apply_filters(scope_query(stmt, user), f)
    if limit:
        stmt = stmt.order_by(Feedback.id.desc()).limit(limit)
    rows = [dict(r._mapping) for r in db.execute(stmt)]
    if f.topic:
        rows = [r for r in rows if f.topic in (r["topics"] or [])]
    return rows


def scope_label(db: Session, f: Filters) -> str:
    bits = []
    if f.course_id and (c := db.get(Course, f.course_id)):
        bits.append(f"{c.code} {c.title}")
    if f.service_id and (s := db.get(Service, f.service_id)):
        bits.append(s.name)
    if f.department_id and (d := db.get(Department, f.department_id)):
        bits.append(d.name)
    if f.kind and not (f.course_id or f.service_id):
        bits.append({"course": "course evaluations", "service": "service reviews", "survey": "general surveys"}[f.kind])
    if f.topic:
        bits.append(f"topic '{f.topic}'")
    if f.semester:
        bits.append(f.semester)
    return ", ".join(bits) if bits else "all feedback"


# ---------------------------------------------------------------- alerts


def recompute_alerts(db: Session) -> int:
    """Flag courses/services/departments whose negative share rose sharply vs. the previous semester."""
    rows = db.execute(select(
        Feedback.semester, Feedback.sentiment, Feedback.course_id, Feedback.service_id,
        Feedback.department_id, Feedback.aspects,
    )).all()
    semesters = sort_semesters(r.semester for r in rows)
    if len(semesters) < 2:
        return 0

    buckets: dict[tuple, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    neg_topics: dict[tuple, Counter] = defaultdict(Counter)
    for r in rows:
        keys = []
        if r.course_id:
            keys.append(("course", r.course_id))
        if r.service_id:
            keys.append(("service", r.service_id))
        if r.department_id:
            keys.append(("department", r.department_id))
        for k in keys:
            buckets[k][r.semester][r.sentiment] += 1
            if r.semester == semesters[-1]:
                for t, lab in (r.aspects or {}).items():
                    if lab == "negative":
                        neg_topics[k][t] += 1

    names = {
        "course": {c.id: (f"{c.code} {c.title}", c.department_id) for c in db.scalars(select(Course))},
        "service": {s.id: (s.name, None) for s in db.scalars(select(Service))},
        "department": {d.id: (d.name, d.id) for d in db.scalars(select(Department))},
    }

    # Compare the latest semester that has enough data with the one before it
    db.execute(delete(Alert).where(Alert.is_read.is_(False)))
    created = 0
    for key, by_sem in buckets.items():
        sems = [s for s in semesters if sum(by_sem[s].values()) >= settings.alert_min_feedback]
        if len(sems) < 2 or sems[-1] != semesters[-1] and sems[-1] != semesters[-2]:
            continue
        cur, prev = sems[-1], sems[-2]
        cur_share = by_sem[cur]["negative"] / sum(by_sem[cur].values())
        prev_share = by_sem[prev]["negative"] / sum(by_sem[prev].values())
        delta = (cur_share - prev_share) * 100
        if delta < settings.alert_threshold_pp:
            continue
        name, dept = names[key[0]].get(key[1], (f"#{key[1]}", None))
        top = neg_topics[key].most_common(1)
        top_topic = top[0][0] if top else None
        exists = db.scalar(select(Alert).where(
            Alert.scope_type == key[0], Alert.scope_id == key[1], Alert.semester == cur))
        if exists:
            continue
        msg = (f"Negative feedback for {name} rose from {round(prev_share * 100)}% in {prev} "
               f"to {round(cur_share * 100)}% in {cur}")
        msg += f", driven mainly by {top_topic.lower()}." if top_topic else "."
        db.add(Alert(
            scope_type=key[0], scope_id=key[1], scope_name=name, department_id=dept,
            semester=cur, previous_semester=prev, negative_share=round(cur_share, 3),
            previous_share=round(prev_share, 3), top_topic=top_topic,
            severity="high" if delta >= settings.alert_threshold_pp * 2 else "medium", message=msg,
        ))
        created += 1
    db.commit()
    return created
