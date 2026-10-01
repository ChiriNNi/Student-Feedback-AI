from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import KINDS, Course, Feedback, Service, SubmissionReceipt, Survey, User
from ..security import admin_only, get_current_user, student_only
from ..services import analyze_into, get_matchers, semester_key

router = APIRouter(prefix="/api/surveys", tags=["surveys"])


class SurveyIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    kind: str
    semester: str = Field(min_length=4, max_length=24)
    status: str = "open"
    question: str = "What did you like, and what should be improved?"


class SubmitIn(BaseModel):
    course_id: int | None = None
    service_id: int | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str = Field(min_length=5, max_length=4000)


def survey_out(s: Survey, responses: int | None = None) -> dict:
    return {
        "id": s.id, "title": s.title, "description": s.description, "kind": s.kind,
        "semester": s.semester, "status": s.status, "question": s.question,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "responses": responses,
    }


@router.get("")
def list_surveys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "student":
        surveys = db.scalars(select(Survey).where(Survey.status == "open")).all()
        done = {(r.survey_id, r.target_key) for r in db.scalars(
            select(SubmissionReceipt).where(SubmissionReceipt.user_id == user.id))}
        courses = db.scalars(select(Course).order_by(Course.code)).all()
        services = db.scalars(select(Service).order_by(Service.name)).all()
        out = []
        for s in sorted(surveys, key=lambda s: (semester_key(s.semester), s.id), reverse=True):
            item = survey_out(s)
            if s.kind == "course":
                item["targets"] = [{"type": "course", "id": c.id, "label": f"{c.code} — {c.title}",
                                    "done": (s.id, f"course:{c.id}") in done} for c in courses]
            elif s.kind == "service":
                item["targets"] = [{"type": "service", "id": v.id, "label": v.name,
                                    "done": (s.id, f"service:{v.id}") in done} for v in services]
            else:
                item["targets"] = [{"type": "general", "id": None, "label": "General",
                                    "done": (s.id, "general") in done}]
            item["completed"] = all(t["done"] for t in item["targets"])
            out.append(item)
        return out

    counts = dict(db.execute(select(Feedback.survey_id, func.count()).group_by(Feedback.survey_id)).all())
    surveys = db.scalars(select(Survey)).all()
    surveys = sorted(surveys, key=lambda s: (semester_key(s.semester), s.id), reverse=True)
    return [survey_out(s, counts.get(s.id, 0)) for s in surveys]


@router.post("/{survey_id}/submit")
def submit(survey_id: int, body: SubmitIn, user: User = Depends(student_only), db: Session = Depends(get_db)):
    survey = db.get(Survey, survey_id)
    if not survey or survey.status != "open":
        raise HTTPException(404, "This survey is not open")

    fb = Feedback(survey_id=survey.id, kind=survey.kind, semester=survey.semester,
                  rating=body.rating, source="form")
    if survey.kind == "course":
        course = db.get(Course, body.course_id or 0)
        if not course:
            raise HTTPException(422, "Please choose a course")
        fb.course_id, fb.department_id = course.id, course.department_id
        target = f"course:{course.id}"
    elif survey.kind == "service":
        service = db.get(Service, body.service_id or 0)
        if not service:
            raise HTTPException(422, "Please choose a service")
        fb.service_id = service.id
        target = f"service:{service.id}"
    else:
        fb.department_id = user.department_id
        target = "general"

    analyze_into(fb, body.text, get_matchers(db))
    # The receipt only proves participation; it has no reference to the feedback row.
    db.add(SubmissionReceipt(user_id=user.id, survey_id=survey.id, target_key=target))
    db.add(fb)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already submitted feedback for this item")
    return {"ok": True, "pii_masked": fb.pii_masked}


@router.post("", dependencies=[Depends(admin_only)])
def create_survey(body: SurveyIn, db: Session = Depends(get_db)):
    _validate(body)
    s = Survey(**body.model_dump())
    db.add(s)
    db.commit()
    return survey_out(s, 0)


@router.put("/{survey_id}", dependencies=[Depends(admin_only)])
def update_survey(survey_id: int, body: SurveyIn, db: Session = Depends(get_db)):
    _validate(body)
    s = db.get(Survey, survey_id)
    if not s:
        raise HTTPException(404, "Survey not found")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return survey_out(s)


@router.delete("/{survey_id}", dependencies=[Depends(admin_only)])
def delete_survey(survey_id: int, db: Session = Depends(get_db)):
    s = db.get(Survey, survey_id)
    if not s:
        raise HTTPException(404, "Survey not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


def _validate(body: SurveyIn):
    if body.kind not in KINDS:
        raise HTTPException(422, f"kind must be one of {KINDS}")
    if body.status not in ("draft", "open", "closed"):
        raise HTTPException(422, "status must be draft, open or closed")
    if semester_key(body.semester) == (0, 0):
        raise HTTPException(422, "semester must look like 'Fall 2026' or 'Spring 2027'")
