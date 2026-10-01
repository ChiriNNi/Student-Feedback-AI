from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Alert, Course, Department, Feedback, Service, TopicCategory, User
from ..nlp.summarizer import aspect_stats, llm_available, llm_summary, local_summary
from ..security import get_current_user, staff_only
from ..services import Filters, feedback_rows, scope_label, scope_query, sort_semesters

router = APIRouter(prefix="/api", tags=["analytics"])


def filters_dep(
    semester: str | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    service_id: int | None = None,
    kind: str | None = None,
    sentiment: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    q: str | None = None,
    survey_id: int | None = None,
) -> Filters:
    return Filters(semester or None, department_id or None, course_id or None, service_id or None,
                   kind or None, sentiment or None, topic or None, language or None, q or None,
                   survey_id or None)


def _kpis(rows: list[dict]) -> dict:
    n = len(rows)
    c = Counter(r["sentiment"] for r in rows)
    ratings = [r["rating"] for r in rows if r.get("rating")]
    pos = c["positive"] / n if n else 0
    neg = c["negative"] / n if n else 0
    return {
        "total": n,
        "positive": c["positive"], "neutral": c["neutral"], "negative": c["negative"],
        "positive_share": round(pos, 4), "negative_share": round(neg, 4),
        "satisfaction_index": round((pos - neg) * 100, 1),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }


def _topic_colors(db: Session) -> dict:
    return {t.name: t.color for t in db.scalars(select(TopicCategory))}


def _all_semesters(db: Session, user: User) -> list[str]:
    stmt = scope_query(select(Feedback.semester).distinct(), user)
    return sort_semesters(db.scalars(stmt).all())


# ------------------------------------------------------------------ meta

@router.get("/meta")
def meta(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    courses_q = select(Course).order_by(Course.code)
    if user.role == "faculty":
        courses_q = courses_q.where(Course.instructor_id == user.id)
    elif user.role == "manager" and user.department_id:
        courses_q = courses_q.where(Course.department_id == user.department_id)
    courses = db.scalars(courses_q).all()
    depts = db.scalars(select(Department).order_by(Department.name)).all()
    if user.role == "manager" and user.department_id:
        depts = [d for d in depts if d.id == user.department_id]
    if user.role == "faculty":
        own = {c.department_id for c in courses}
        depts = [d for d in depts if d.id in own]
    services = [] if user.role == "faculty" else db.scalars(select(Service).order_by(Service.name)).all()
    sems = _all_semesters(db, user) if user.role != "student" else []
    return {
        "semesters": sems,
        "current_semester": sems[-1] if sems else None,
        "departments": [{"id": d.id, "code": d.code, "name": d.name} for d in depts],
        "courses": [{"id": c.id, "code": c.code, "title": c.title, "department_id": c.department_id,
                     "instructor": c.instructor.name if c.instructor else None} for c in courses],
        "services": [{"id": s.id, "name": s.name, "category": s.category} for s in services],
        "topics": [{"id": t.id, "name": t.name, "color": t.color}
                   for t in db.scalars(select(TopicCategory).where(TopicCategory.is_active.is_(True))
                                       .order_by(TopicCategory.name))],
        "llm_enabled": llm_available(),
    }


# ------------------------------------------------------------------ overview

@router.get("/analytics/overview")
def overview(f: Filters = Depends(filters_dep), user: User = Depends(staff_only), db: Session = Depends(get_db)):
    sems = _all_semesters(db, user)
    target = f.semester or (sems[-1] if sems else None)
    rows = feedback_rows(db, user, f)
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
    topics = aspect_stats(rows)
    for t in topics:
        t["color"] = colors.get(t["topic"], "#8b5cff")
    problems = sorted([t for t in topics if t["negative"] >= 3],
                      key=lambda t: (t["negative"] * t["negative_share"]), reverse=True)[:5]

    alerts_q = select(Alert).where(Alert.is_read.is_(False))
    alerts = _visible_alerts(db.scalars(alerts_q).all(), user, db)

    return {
        **kpi,
        "delta": delta,
        "topics": topics,
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
