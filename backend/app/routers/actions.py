from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ACTION_STATUSES, Action, Alert, Course, User
from ..security import managers, staff_only
from .analytics import _visible_alerts

router = APIRouter(prefix="/api", tags=["actions & alerts"])


class ActionIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    topic: str | None = None
    course_id: int | None = None
    service_id: int | None = None
    owner: str = ""
    status: str = "planned"
    due_date: date | None = None


def action_out(a: Action) -> dict:
    return {
        "id": a.id, "title": a.title, "description": a.description, "topic": a.topic,
        "course_id": a.course_id, "service_id": a.service_id,
        "target": (f"{a.course.code} — {a.course.title}" if a.course else a.service.name if a.service else None),
        "owner": a.owner, "status": a.status,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "overdue": bool(a.due_date and a.due_date < date.today() and a.status != "done"),
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _visible_actions(user: User):
    stmt = select(Action)
    if user.role == "manager" and user.department_id:
        stmt = stmt.where(or_(Action.department_id == user.department_id, Action.service_id.is_not(None)))
    elif user.role == "faculty":
        own = select(Course.id).where(Course.instructor_id == user.id)
        stmt = stmt.where(Action.course_id.in_(own))
    return stmt


@router.get("/actions")
def list_actions(user: User = Depends(staff_only), db: Session = Depends(get_db)):
    items = db.scalars(_visible_actions(user).order_by(Action.created_at.desc())).all()
    return [action_out(a) for a in items]


@router.post("/actions")
def create_action(body: ActionIn, user: User = Depends(managers), db: Session = Depends(get_db)):
    _validate(body)
    a = Action(**body.model_dump(), created_by=user.id)
    if a.course_id and (c := db.get(Course, a.course_id)):
        a.department_id = c.department_id
    db.add(a)
    db.commit()
    return action_out(a)


@router.put("/actions/{action_id}")
def update_action(action_id: int, body: ActionIn, user: User = Depends(managers), db: Session = Depends(get_db)):
    _validate(body)
    a = db.scalar(_visible_actions(user).where(Action.id == action_id))
    if not a:
        raise HTTPException(404, "Action not found")
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    if a.course_id and (c := db.get(Course, a.course_id)):
        a.department_id = c.department_id
    db.commit()
    return action_out(a)


@router.delete("/actions/{action_id}")
def delete_action(action_id: int, user: User = Depends(managers), db: Session = Depends(get_db)):
    a = db.scalar(_visible_actions(user).where(Action.id == action_id))
    if not a:
        raise HTTPException(404, "Action not found")
    db.delete(a)
    db.commit()
    return {"ok": True}


def _validate(body: ActionIn):
    if body.status not in ACTION_STATUSES:
        raise HTTPException(422, f"status must be one of {ACTION_STATUSES}")


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
