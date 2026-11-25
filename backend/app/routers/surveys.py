"""Administrator survey lifecycle. Student submissions use the anonymous evaluations router."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Feedback, Survey, SurveyQuestion
from ..security import admin_only
from ..services import sort_semesters
from .evaluations import _question_out, _questions

admin_router = APIRouter(prefix="/api/admin/surveys", tags=["survey management"],
                         dependencies=[Depends(admin_only)])

DEFAULT_PROMPT = "What did you like, and what should be improved?"


class QuestionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=300)


class SurveyIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    kind: Literal["course", "service", "survey"]
    semester: str = Field(pattern=r"^(Winter|Spring|Summer|Fall|Autumn) [0-9]{4}$")
    question: str = Field(default=DEFAULT_PROMPT, min_length=1, max_length=300)
    questions: list[QuestionIn] | None = Field(default=None, max_length=30)

    @field_validator("semester", mode="before")
    @classmethod
    def normalize_semester(cls, value):
        return " ".join(value.split()).title() if isinstance(value, str) else value


class StatusIn(BaseModel):
    status: Literal["open", "closed"]


def _get_survey(db: Session, survey_id: int) -> Survey:
    survey = db.get(Survey, survey_id, with_for_update=True)
    if survey is None or survey.is_demo_archive:
        raise HTTPException(404, "Survey not found")
    return survey


def _response_count(db: Session, survey_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Feedback).where(Feedback.survey_id == survey_id))


def _survey_out(db: Session, survey: Survey, responses: int) -> dict:
    return {
        "id": survey.id, "title": survey.title, "description": survey.description, "kind": survey.kind,
        "semester": survey.semester, "status": survey.status, "question": survey.question, "responses": responses,
        "questions": [_question_out(q) for q in _questions(db, survey.kind, survey.id)],
        "form_locked": survey.status == "open" or bool(responses),
    }


def _replace_questions(db: Session, survey: Survey, questions: list[QuestionIn]) -> None:
    if survey.kind != "survey" and not questions:
        raise HTTPException(422, "Course and service forms need at least one rating question")
    db.execute(delete(SurveyQuestion).where(SurveyQuestion.survey_id == survey.id))
    db.add_all(SurveyQuestion(survey_id=survey.id, kind=survey.kind, position=i,
                              label=q.label, text=q.text) for i, q in enumerate(questions))
    db.flush()


@admin_router.get("")
def list_surveys(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Feedback.survey_id, func.count()).group_by(Feedback.survey_id)).all())
    surveys = db.scalars(select(Survey).where(Survey.is_demo_archive.is_(False)).order_by(Survey.id.desc())).all()
    return {
        "items": [_survey_out(db, survey, counts.get(survey.id, 0)) for survey in surveys],
        "semesters": sort_semesters(s.semester for s in surveys),
    }


@admin_router.post("", status_code=201)
def create_survey(body: SurveyIn, db: Session = Depends(get_db)):
    survey = Survey(**body.model_dump(exclude={"questions"}), status="draft")
    db.add(survey)
    db.flush()
    _replace_questions(db, survey, body.questions or [])
    db.commit()
    return _survey_out(db, survey, 0)


@admin_router.put("/{survey_id}")
def update_survey(survey_id: int, body: SurveyIn, db: Session = Depends(get_db)):
    survey = _get_survey(db, survey_id)
    responses = _response_count(db, survey_id)
    questions = body.questions
    if survey.status == "open" or responses:
        original = [QuestionIn(label=q.label, text=q.text) for q in _questions(db, survey.kind, survey.id)]
        if ((body.kind, body.semester, body.question) != (survey.kind, survey.semester, survey.question)
                or (questions is not None and questions != original)):
            raise HTTPException(409, "Published forms and forms with responses keep their original questions, type and semester")
        questions = None
    elif body.kind != survey.kind and questions is None:
        raise HTTPException(422, "Provide the questions for the new survey type")
    for key, value in body.model_dump(exclude={"questions"}).items():
        setattr(survey, key, value)
    if questions is not None:
        _replace_questions(db, survey, questions)
    db.commit()
    return _survey_out(db, survey, responses)


@admin_router.patch("/{survey_id}/status")
def change_status(survey_id: int, body: StatusIn, db: Session = Depends(get_db)):
    survey = _get_survey(db, survey_id)
    if body.status == "closed" and survey.status == "draft":
        raise HTTPException(409, "Only a published survey can be closed")
    if body.status == "open" and survey.kind != "survey" and not _questions(db, survey.kind, survey.id):
        raise HTTPException(422, "Add a rating question before publishing this form")
    survey.status = body.status
    db.commit()
    return _survey_out(db, survey, _response_count(db, survey_id))
