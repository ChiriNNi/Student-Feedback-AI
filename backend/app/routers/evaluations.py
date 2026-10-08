"""Sprint 2: anonymous course evaluations and service reviews.

Anonymity model (story 1.3): a submission writes two rows that share nothing
but the survey —
  * `feedback` holds the answer (ratings + PII-masked comment) and has no user column;
  * `submission_receipts` holds (user, survey, target) only, to stop double voting.
Both carry day-level dates at most, and receipts have no sequential id, so the
two tables can't be joined back together by id order or by timestamp.
"""
import time
from datetime import date, datetime, time as dtime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Course, Feedback, Service, SubmissionReceipt, Survey, SurveyQuestion, User
from ..nlp.analyzer import detect_language
from ..nlp.pii import mask_pii_report, names_pattern
from ..security import staff_only, student_only
from ..services import scope_query, semester_key

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])

FORM_KINDS = ("course", "service")


class SubmitIn(BaseModel):
    course_id: int | None = None
    service_id: int | None = None
    ratings: dict[int, int]  # {question_id: 1..5}
    comment: str = Field(default="", max_length=2000)


def _questions(db: Session, kind: str) -> list[SurveyQuestion]:
    return db.scalars(select(SurveyQuestion).where(SurveyQuestion.kind == kind, SurveyQuestion.is_active.is_(True))
                      .order_by(SurveyQuestion.position, SurveyQuestion.id)).all()


def _question_out(q: SurveyQuestion) -> dict:
    return {"id": q.id, "label": q.label, "text": q.text}


# Names of everyone with an account, refreshed at most once a minute.
_names_cache: dict = {"at": 0.0, "rx": None}


def _known_names(db: Session):
    if time.monotonic() - _names_cache["at"] > 60:
        _names_cache["rx"] = names_pattern(db.scalars(select(User.name)))
        _names_cache["at"] = time.monotonic()
    return _names_cache["rx"]


# ------------------------------------------------------------------ student

@router.get("/forms")
def open_forms(user: User = Depends(student_only), db: Session = Depends(get_db)):
    """Open course-evaluation / service-review surveys, with what this student has already answered."""
    surveys = db.scalars(select(Survey).where(Survey.status == "open", Survey.kind.in_(FORM_KINDS))).all()
    done = {(r.survey_id, r.target_key) for r in db.scalars(
        select(SubmissionReceipt).where(SubmissionReceipt.user_id == user.id))}

    out = []
    # Course evaluations first, newest semester first within a kind
    for s in sorted(surveys, key=lambda s: (FORM_KINDS.index(s.kind), [-n for n in semester_key(s.semester)], -s.id)):
        if s.kind == "course":
            targets = [{
                "id": c.id, "key": f"course:{c.id}", "title": c.title, "code": c.code,
                "department": c.department.name if c.department else None,
                "instructor": c.instructor.name if c.instructor else None,
                "own_department": c.department_id == user.department_id,
            } for c in db.scalars(select(Course).order_by(Course.code))]
        else:
            targets = [{"id": v.id, "key": f"service:{v.id}", "title": v.name, "code": None,
                        "department": v.category, "instructor": None, "own_department": False}
                       for v in db.scalars(select(Service).order_by(Service.name))]
        for t in targets:
            t["done"] = (s.id, t["key"]) in done
        out.append({
            "id": s.id, "title": s.title, "description": s.description, "kind": s.kind,
            "semester": s.semester, "comment_prompt": s.question,
            "questions": [_question_out(q) for q in _questions(db, s.kind)],
            "targets": targets,
        })
    return out


@router.post("/{survey_id}/submit")
def submit(survey_id: int, body: SubmitIn, user: User = Depends(student_only), db: Session = Depends(get_db)):
    survey = db.get(Survey, survey_id)
    if not survey or survey.status != "open" or survey.kind not in FORM_KINDS:
        raise HTTPException(404, "This form is not open")

    # Day precision only — an exact timestamp could be matched against the receipt or server logs.
    today = datetime.combine(date.today(), dtime.min, tzinfo=timezone.utc)
    fb = Feedback(survey_id=survey.id, kind=survey.kind, semester=survey.semester, source="form", created_at=today)
    if survey.kind == "course":
        course = db.get(Course, body.course_id or 0)
        if not course:
            raise HTTPException(422, "Please choose a course")
        fb.course_id, fb.department_id = course.id, course.department_id
        target = f"course:{course.id}"
    else:
        service = db.get(Service, body.service_id or 0)
        if not service:
            raise HTTPException(422, "Please choose a service")
        fb.service_id = service.id
        target = f"service:{service.id}"

    questions = _questions(db, survey.kind)
    expected = {q.id for q in questions}
    if set(body.ratings) != expected:
        raise HTTPException(422, "Please answer every rating question")
    if any(not 1 <= v <= 5 for v in body.ratings.values()):
        raise HTTPException(422, "Ratings must be between 1 and 5")
    fb.ratings = {str(k): v for k, v in body.ratings.items()}
    fb.rating = round(sum(body.ratings.values()) / len(body.ratings))

    # Story 1.4: personal data is removed before anything is stored — the raw comment never reaches the DB.
    raw = body.comment.strip()
    masked, removed = mask_pii_report(raw, _known_names(db)) if raw else ("", {})
    fb.text = masked
    fb.pii_masked = bool(removed)
    fb.language = detect_language(masked) if masked else "en"

    db.add(SubmissionReceipt(user_id=user.id, survey_id=survey.id, target_key=target))
    db.add(fb)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # the receipt's primary key already exists
        raise HTTPException(409, "You have already submitted feedback for this item")
    return {"ok": True, "comment": masked, "removed": dict(removed)}


# ------------------------------------------------------------------ staff

@router.get("/responses")
def responses(
    kind: str | None = Query(None, pattern="^(course|service)$"),
    course_id: int | None = None, service_id: int | None = None,
    user: User = Depends(staff_only), db: Session = Depends(get_db),
):
    """Submitted responses, scoped by role: faculty see their own courses, managers their department."""
    stmt = scope_query(select(Feedback), user).where(Feedback.kind.in_(FORM_KINDS))
    if kind:
        stmt = stmt.where(Feedback.kind == kind)
    if course_id:
        stmt = stmt.where(Feedback.course_id == course_id)
    if service_id:
        stmt = stmt.where(Feedback.service_id == service_id)
    items = db.scalars(stmt.order_by(Feedback.created_at.desc(), Feedback.id.desc())).all()

    questions = db.scalars(select(SurveyQuestion).order_by(SurveyQuestion.position, SurveyQuestion.id)).all()
    return {
        "scope": _scope_label(user),
        "questions": {k: [_question_out(q) for q in questions if q.kind == k] for k in FORM_KINDS},
        "items": [{
            "id": fb.id, "kind": fb.kind, "semester": fb.semester,
            "date": fb.created_at.date().isoformat() if fb.created_at else None,
            "target": (f"{fb.course.code} — {fb.course.title}" if fb.course
                       else fb.service.name if fb.service else "Removed item"),
            "course_id": fb.course_id, "service_id": fb.service_id,
            "department": fb.department.name if fb.department else None,
            "ratings": fb.ratings or {}, "rating": fb.rating,
            "comment": fb.text, "pii_masked": fb.pii_masked, "language": fb.language,
        } for fb in items],
    }


def _scope_label(user: User) -> str:
    if user.role == "faculty":
        return "Responses for the courses you teach"
    if user.role == "manager" and user.department_id:
        return f"Responses for {user.department.name} and university services"
    return "All responses across the university"
