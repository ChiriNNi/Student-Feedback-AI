from collections import Counter, defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Alert, Course, Department, Faculty, Feedback, Service, TopicCategory, User
from ..nlp.summarizer import aspect_stats, llm_available, llm_summary, local_summary
from ..security import staff_only
from ..services import (
    Filters, feedback_rows, scope_label, scope_query, scoped_courses, scoped_departments, sort_semesters,
)

router = APIRouter(prefix="/api", tags=["analytics"])


FilterID = Annotated[int | None, Query(gt=0)]


def filters_dep(
    user: User = Depends(staff_only),
    db: Session = Depends(get_db),
    semester: str | None = None,
    faculty_id: FilterID = None,
    department_id: FilterID = None,
    course_id: FilterID = None,
    service_id: FilterID = None,
    instructor_id: FilterID = None,
    kind: Annotated[str | None, Query(pattern="^(course|service|survey)$")] = None,
    sentiment: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    q: str | None = None,
    survey_id: FilterID = None,
) -> Filters:
    departments = scoped_departments(user)
    if faculty_id:
        departments = departments.where(Department.faculty_id == faculty_id)
    if department_id:
        departments = departments.where(Department.id == department_id)

    courses = scoped_courses(user).where(Course.department_id.in_(departments.with_only_columns(Department.id)))
    if course_id:
        courses = courses.where(Course.id == course_id)
    if instructor_id:
        courses = courses.where(Course.instructor_id == instructor_id)

    invalid = (
        (semester and semester not in _all_semesters(db, user))
        or ((faculty_id or department_id) and db.scalar(departments.limit(1)) is None)
        or ((course_id or instructor_id) and db.scalar(courses.limit(1)) is None)
        or (service_id and (
            user.role == "faculty" or faculty_id or department_id or course_id or instructor_id
            or db.get(Service, service_id) is None
        ))
    )
    if invalid:
        raise HTTPException(422, "The selected dashboard filters are incompatible or unavailable in your scope.")
    return Filters(
        semester=semester, faculty_id=faculty_id, department_id=department_id, course_id=course_id,
        service_id=service_id, instructor_id=instructor_id, kind=kind, sentiment=sentiment,
        topic=topic, language=language, q=q, survey_id=survey_id,
    )


def _response_rating(row: dict) -> float | None:
    answers = [value for value in (row["ratings"] or {}).values()
               if type(value) is int and 1 <= value <= 5]
    if answers:
        return sum(answers) / len(answers)
    rating = row["rating"]
    return rating if rating is not None and 1 <= rating <= 5 else None


def _kpis(rows: list[dict]) -> dict:
    sentiments = ("positive", "neutral", "negative")
    counts = Counter(row["sentiment"] for row in rows
                     if row["confidence"] > 0 or row["is_corrected"])
    analyzed = sum(counts[tone] for tone in sentiments)
    shares = {tone: round(counts[tone] / analyzed, 4) if analyzed else 0
              for tone in sentiments}
    ratings = [rating for row in rows if (rating := _response_rating(row)) is not None]
    return {
        "total": len(rows), "analyzed": analyzed, "rated": len(ratings),
        **{tone: counts[tone] for tone in sentiments},
        **{f"{tone}_share": shares[tone] for tone in sentiments},
        "satisfaction_index": round((shares["positive"] - shares["negative"]) * 100, 1),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }


def _topic_mentions(rows: list[dict]) -> Counter:
    mentions = Counter()
    for row in rows:
        mentions.update(set(row["topics"] or []) | set(row["aspects"] or {}))
    return mentions


def _topic_colors(db: Session) -> dict:
    return {t.name: t.color for t in db.scalars(select(TopicCategory))}


def _all_semesters(db: Session, user: User) -> list[str]:
    stmt = scope_query(select(Feedback.semester).distinct(), user)
    return sort_semesters(db.scalars(stmt).all())


# ------------------------------------------------------------------ meta

@router.get("/meta")
def meta(user: User = Depends(staff_only), db: Session = Depends(get_db)):
    courses = db.scalars(scoped_courses(user).order_by(Course.code)).all()
    depts = db.scalars(scoped_departments(user).order_by(Department.name)).all()
    faculty_ids = {d.faculty_id for d in depts if d.faculty_id is not None}
    faculties = db.scalars(select(Faculty).where(Faculty.id.in_(faculty_ids)).order_by(Faculty.name))
    services = [] if user.role == "faculty" else db.scalars(select(Service).order_by(Service.name)).all()
    instructors = sorted({c.instructor for c in courses if c.instructor}, key=lambda u: u.name)
    sems = _all_semesters(db, user)
    return {
        "semesters": sems,
        "current_semester": sems[-1] if sems else None,
        "faculties": [{"id": f.id, "code": f.code, "name": f.name} for f in faculties],
        "departments": [{"id": d.id, "code": d.code, "name": d.name, "faculty_id": d.faculty_id} for d in depts],
        "courses": [{"id": c.id, "code": c.code, "title": c.title, "department_id": c.department_id,
                     "instructor": c.instructor.name if c.instructor else None,
                     "instructor_id": c.instructor_id} for c in courses],
        "instructors": [{"id": u.id, "name": u.name} for u in instructors],
        "services": [{"id": s.id, "name": s.name, "category": s.category} for s in services],
        "topics": [{"id": t.id, "name": t.name, "color": t.color}
                   for t in db.scalars(select(TopicCategory).where(TopicCategory.is_active.is_(True))
                                       .order_by(TopicCategory.name))],
        "llm_enabled": llm_available(),
    }


# ------------------------------------------------------------------ overview

@router.get("/analytics/overview")
def overview(f: Filters = Depends(filters_dep), user: User = Depends(staff_only), db: Session = Depends(get_db)):
    """Sprint 3 dashboard data (stories 3.1–3.4) for the responses the user's role may see."""
    sems = _all_semesters(db, user)
    target = f.semester or (sems[-1] if sems else None)
    # Role scoping happens here on the server: faculty get their own courses,
    # managers their department plus university services, admins everything.
    rows = feedback_rows(db, user, f)
    # Story 3.1: sentiment counts and shares, net sentiment and the average rating.
    kpi = _kpis(rows)

    # Period-over-period deltas: selected (or latest) semester vs the one before it
    delta = None
    if target and target in sems and sems.index(target) > 0:
        prev = sems[sems.index(target) - 1]
        cur_rows = rows if f.semester else [r for r in rows if r["semester"] == target]
        pf = Filters(**{**f.__dict__, "semester": prev})
        a, b = _kpis(cur_rows), _kpis(feedback_rows(db, user, pf))
        delta = {
            "semester": target, "previous": prev,
            "total": a["total"] - b["total"],
            "satisfaction_index": round(a["satisfaction_index"] - b["satisfaction_index"], 1),
            "negative_share": round(a["negative_share"] - b["negative_share"], 4),
            "avg_rating": round((a["avg_rating"] or 0) - (b["avg_rating"] or 0), 2)
            if a["avg_rating"] and b["avg_rating"] else None,
        }

    colors = _topic_colors(db)
    # Stories 3.2 and 3.3: for every topic, how many responses mention it and how many
    # of those mentions are positive, neutral or negative (from the stored aspects).
    topics = aspect_stats(rows)
    for t in topics:
        t["color"] = colors.get(t["topic"], "#8b5cff")
    # Story 3.4: a topic becomes a common problem once at least three responses mention it
    # negatively. Ranked by negative mentions x negative share, so 6 negative out of 6
    # (score 6) comes before 6 out of 12 (score 3). Only the top five are returned.
    problems = sorted([t for t in topics if t["negative"] >= 3],
                      key=lambda t: (t["negative"] * t["negative_share"]), reverse=True)[:5]

    alerts_q = select(Alert).where(Alert.is_read.is_(False))
    alerts = _visible_alerts(db.scalars(alerts_q).all(), user, db)

    return {
        **kpi,
        "delta": delta,
        "topics": topics,
        "top_topics": [{"topic": topic, "total": count} for topic, count in
                       sorted(_topic_mentions(rows).items(), key=lambda item: (-item[1], item[0]))[:5]],
        "problems": problems,
        "languages": dict(Counter(r["language"] for r in rows)),
        "kinds": dict(Counter(r["kind"] for r in rows)),
        "open_alerts": len(alerts),
        "scope": scope_label(db, f),
    }


def _visible_alerts(alerts, user: User, db: Session):
    if user.role == "admin" or (user.role == "manager" and not user.department_id):
        return alerts
    if user.role == "manager":
        return [a for a in alerts if a.department_id == user.department_id or a.scope_type == "service"]
    own = set(db.scalars(select(Course.id).where(Course.instructor_id == user.id)))
    return [a for a in alerts if a.scope_type == "course" and a.scope_id in own]


# ------------------------------------------------------------------ trends

@router.get("/analytics/trends")
def trends(f: Filters = Depends(filters_dep), user: User = Depends(staff_only), db: Session = Depends(get_db)):
    f.semester = None
    rows = feedback_rows(db, user, f)
    by_sem: dict[str, list] = defaultdict(list)
    for r in rows:
        by_sem[r["semester"]].append(r)
    sems = sort_semesters(by_sem.keys())
    series = [{"semester": s, **_kpis(by_sem[s])} for s in sems]

    topic_totals = Counter()
    for r in rows:
        topic_totals.update((r["aspects"] or {}).keys())
    top_topics = [t for t, _ in topic_totals.most_common(8)]
    topic_series = []
    for s in sems:
        point = {"semester": s}
        stats = {a["topic"]: a for a in aspect_stats(by_sem[s])}
        for t in top_topics:
            a = stats.get(t)
            point[t] = round(a["negative_share"] * 100, 1) if a else None
            point[f"{t}__mentions"] = a["total"] if a else 0
        topic_series.append(point)
    colors = _topic_colors(db)
    return {
        "series": series,
        "topics": [{"topic": t, "color": colors.get(t, "#8b5cff")} for t in top_topics],
        "topic_series": topic_series,
    }


# ------------------------------------------------------------------ compare

@router.get("/analytics/compare")
def compare(by: str = Query("department", pattern="^(department|course|service)$"),
            f: Filters = Depends(filters_dep), user: User = Depends(staff_only), db: Session = Depends(get_db)):
    rows = feedback_rows(db, user, f)
    key = {"department": "department_id", "course": "course_id", "service": "service_id"}[by]
    groups: dict[int, list] = defaultdict(list)
    for r in rows:
        if r[key]:
            groups[r[key]].append(r)

    if by == "department":
        names = {d.id: d.name for d in db.scalars(select(Department))}
    elif by == "course":
        names = {c.id: f"{c.code} — {c.title}" for c in db.scalars(select(Course))}
    else:
        names = {s.id: s.name for s in db.scalars(select(Service))}

    out = []
    for gid, items in groups.items():
        k = _kpis(items)
        asp = aspect_stats(items)
        worst = max((a for a in asp if a["total"] >= 3), key=lambda a: a["negative_share"], default=None)
        best = max((a for a in asp if a["total"] >= 3), key=lambda a: a["positive_share"], default=None)
        out.append({"id": gid, "name": names.get(gid, f"#{gid}"), **k,
                    "top_problem": worst["topic"] if worst and worst["negative_share"] >= 0.25 else None,
                    "top_strength": best["topic"] if best and best["positive_share"] >= 0.5 else None})
    out.sort(key=lambda x: x["satisfaction_index"], reverse=True)
    return out


# ------------------------------------------------------------------ keywords

@router.get("/analytics/keywords")
def keywords(limit: int = Query(60, le=150), f: Filters = Depends(filters_dep),
             user: User = Depends(staff_only), db: Session = Depends(get_db)):
    rows = feedback_rows(db, user, f)
    count = Counter()
    score = defaultdict(float)
    for r in rows:
        for k in set(r["keywords"] or []):
            count[k] += 1
            score[k] += r["sentiment_score"] or 0
    return [{"word": w, "count": c, "sentiment": round(score[w] / c, 3)} for w, c in count.most_common(limit)]


# ------------------------------------------------------------------ summary

@router.get("/analytics/summary")
def summary(ai: bool = False, f: Filters = Depends(filters_dep),
            user: User = Depends(staff_only), db: Session = Depends(get_db)):
    rows = feedback_rows(db, user, f)
    label = scope_label(db, f)
    base = local_summary(rows, label)
    base["scope"] = label
    if ai:
        if not llm_available():
            raise HTTPException(400, "AI summaries are not configured. Set ANTHROPIC_API_KEY in .env.")
        base = llm_summary(rows, base, label)
    colors = _topic_colors(db)
    for a in base.get("aspects", []):
        a["color"] = colors.get(a["topic"], "#8b5cff")
    return base
