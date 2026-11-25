from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Action, Alert, Course, Department, Service, User
from ..nlp.summarizer import aspect_stats
from ..security import managers, staff_only
from ..services import Filters, feedback_rows, scoped_courses, scoped_departments
from .analytics import _visible_alerts, filters_dep

router = APIRouter(prefix="/api", tags=["actions & alerts"])


ActionStatus = Literal["planned", "in_progress", "done"]


class ActionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    topic: str | None = Field(default=None, max_length=80)
    course_id: int | None = Field(default=None, gt=0)
    service_id: int | None = Field(default=None, gt=0)
    department_id: int | None = Field(default=None, gt=0)
    owner: str = Field(default="", max_length=160)
    status: ActionStatus = "planned"
    due_date: date | None = None


class ActionStatusIn(BaseModel):
    status: ActionStatus


def action_out(a: Action) -> dict:
    return {
        "id": a.id, "title": a.title, "description": a.description, "topic": a.topic,
        "course_id": a.course_id, "service_id": a.service_id, "department_id": a.department_id,
        "target": (f"{a.course.code} — {a.course.title}" if a.course else a.service.name if a.service
                   else a.department.name if a.department else None),
        "owner": a.owner, "status": a.status,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "overdue": bool(a.due_date and a.due_date < date.today() and a.status != "done"),
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _visible_actions(user: User):
    stmt = select(Action)
    if user.role == "manager" and user.department_id:
        stmt = stmt.where(or_(Action.course_id.in_(scoped_courses(user).with_only_columns(Course.id)),
                              Action.course_id.is_(None) & (Action.department_id == user.department_id),
                              Action.service_id.is_not(None)))
    elif user.role == "faculty":
        own = select(Course.id).where(Course.instructor_id == user.id)
        stmt = stmt.where(Action.course_id.in_(own))
    return stmt


@router.get("/actions")
def list_actions(user: User = Depends(staff_only), db: Session = Depends(get_db)):
    items = db.scalars(_visible_actions(user).order_by(Action.created_at.desc())).all()
    return [action_out(a) for a in items]


@router.get("/actions/problems")
def action_problems(f: Filters = Depends(filters_dep), user: User = Depends(managers), db: Session = Depends(get_db)):
    if not (f.course_id or f.service_id or f.department_id):
        f.department_id = user.department_id
    return _recurring_problems(db, user, f)


@router.post("/actions", status_code=201)
def create_action(body: ActionIn, user: User = Depends(managers), db: Session = Depends(get_db)):
    a = Action(**_action_values(body, user, db), created_by=user.id)
    db.add(a)
    db.commit()
    return action_out(a)


@router.put("/actions/{action_id}")
def update_action(action_id: int, body: ActionIn, user: User = Depends(managers), db: Session = Depends(get_db)):
    a = _get_action(action_id, user, db)
    for k, v in _action_values(body, user, db, a).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return action_out(a)


@router.patch("/actions/{action_id}/status")
def change_action_status(action_id: int, body: ActionStatusIn, user: User = Depends(managers), db: Session = Depends(get_db)):
    a = _get_action(action_id, user, db)
    a.status = body.status
    db.commit()
    return action_out(a)


@router.delete("/actions/{action_id}")
def delete_action(action_id: int, user: User = Depends(managers), db: Session = Depends(get_db)):
    db.delete(_get_action(action_id, user, db))
    db.commit()
    return {"ok": True}


def _get_action(action_id: int, user: User, db: Session) -> Action:
    a = db.scalar(_visible_actions(user).where(Action.id == action_id).with_for_update())
    if not a:
        raise HTTPException(404, "Action not found")
    return a


def _action_values(body: ActionIn, user: User, db: Session, current: Action | None = None) -> dict:
    if sum(value is not None for value in (body.course_id, body.service_id, body.department_id)) > 1:
        raise HTTPException(422, "Choose one action scope")
    department = body.department_id or user.department_id
    if body.course_id:
        course = db.scalar(scoped_courses(user).where(Course.id == body.course_id))
        if not course:
            raise HTTPException(422, "Course is outside your access scope")
        department = course.department_id
    elif body.service_id:
        if not db.get(Service, body.service_id):
            raise HTTPException(422, "Service does not exist")
        department = None
    elif body.department_id and not db.scalar(scoped_departments(user).where(Department.id == body.department_id)):
        raise HTTPException(422, "Department is outside your access scope")

    topic = body.topic or None
    previous_link = (current.topic, current.course_id, current.service_id, current.department_id) if current else None
    if topic and previous_link != (topic, body.course_id, body.service_id, department):
        scope = Filters(course_id=body.course_id, service_id=body.service_id,
                        department_id=department if not body.course_id else None)
        if not any(problem["topic"] == topic for problem in _recurring_problems(db, user, scope)):
            raise HTTPException(422, "Choose a recurring negative theme in the selected scope")
    return {**body.model_dump(), "department_id": department, "topic": topic}


def _recurring_problems(db: Session, user: User, scope: Filters) -> list[dict]:
    problems = [p for p in aspect_stats(feedback_rows(db, user, scope)) if p["negative"] >= 3]
    return sorted(problems, key=lambda p: (-p["negative"], -p["negative_share"], p["topic"]))


# ------------------------------------------------------------------ alerts

def alert_out(a: Alert) -> dict:
    return {
        "id": a.id, "scope_type": a.scope_type, "scope_id": a.scope_id, "scope_name": a.scope_name,
        "semester": a.semester, "previous_semester": a.previous_semester,
        "negative_share": a.negative_share, "previous_share": a.previous_share,
        "top_topic": a.top_topic, "severity": a.severity, "message": a.message, "is_read": a.is_read,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/alerts")
def list_alerts(include_read: bool = False, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    stmt = select(Alert).order_by(Alert.is_read, Alert.severity.asc(), Alert.created_at.desc())
    if not include_read:
        stmt = stmt.where(Alert.is_read.is_(False))
    return [alert_out(a) for a in _visible_alerts(db.scalars(stmt).all(), user, db)]


@router.post("/alerts/{alert_id}/read")
def read_alert(alert_id: int, user: User = Depends(staff_only), db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a or a not in _visible_alerts([a], user, db):
        raise HTTPException(404, "Alert not found")
    a.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/alerts/recompute", dependencies=[Depends(managers)])
def recompute(db: Session = Depends(get_db)):
    from ..services import recompute_alerts
    return {"created": recompute_alerts(db)}
