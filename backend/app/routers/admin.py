import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ROLES, Action, Alert, AnalysisCorrection, Course, Department, Feedback, Service, TopicCategory, User
from ..nlp.analyzer import label_for
from ..passwords import password_problem
from ..security import admin_only, get_current_user, hash_password, revoke_sessions
from .auth import user_out

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_only)])


# ------------------------------------------------------------------ users

class UserIn(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    name: str = Field(min_length=2, max_length=160)
    role: str
    student_id: str | None = None
    department_id: int | None = None
    password: str | None = Field(default=None, max_length=200)  # strength checked by password_problem()
    is_active: bool = True


class BanIn(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


def admin_user_out(u: User) -> dict:
    return {
        **user_out(u),
        "is_active": u.is_active,
        "ban_reason": u.ban_reason,
        "banned_at": u.banned_at.isoformat() if u.banned_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _get_other_user(user_id: int, me: User, db: Session, action: str) -> User:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == me.id:
        raise HTTPException(400, f"You cannot {action} your own account")
    return u


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.role, User.name)).all()
    return [admin_user_out(u) for u in users]


@router.post("/users")
def create_user(body: UserIn, db: Session = Depends(get_db)):
    _check_user(body, db)
    if not body.password:
        raise HTTPException(422, "Password is required for new users")
    _check_password(body)
    u = User(email=body.email.lower().strip(), name=body.name.strip(), role=body.role,
             student_id=body.student_id or None, department_id=body.department_id,
             password_hash=hash_password(body.password), is_active=True)
    db.add(u)
    db.commit()
    return admin_user_out(u)


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserIn, db: Session = Depends(get_db),
                me: User = Depends(get_current_user)):
    # Ban status is deliberately NOT editable here — only via /ban and /unban,
    # so a routine profile edit can never silently lift a ban.
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    _check_user(body, db, u.id)
    if u.id == me.id and body.role != "admin":
        raise HTTPException(400, "You cannot remove your own admin access")
    u.email, u.name, u.role = body.email.lower().strip(), body.name.strip(), body.role
    u.student_id, u.department_id = body.student_id or None, body.department_id
    if body.password:
        _check_password(body)
        u.password_hash = hash_password(body.password)
        u.failed_attempts, u.locked_until = 0, None
        revoke_sessions(u)  # an admin password reset signs the user out everywhere
    db.commit()
    return admin_user_out(u)


@router.post("/users/{user_id}/ban")
def ban_user(user_id: int, body: BanIn, db: Session = Depends(get_db),
             me: User = Depends(get_current_user)):
    u = _get_other_user(user_id, me, db, "ban")
    u.is_active = False
    u.ban_reason = (body.reason or "").strip() or None
    u.banned_at = datetime.now(timezone.utc)
    db.commit()
    # Existing sessions die immediately: get_current_user rejects inactive accounts.
    return admin_user_out(u)


@router.post("/users/{user_id}/unban")
def unban_user(user_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    u = _get_other_user(user_id, me, db, "unban")
    u.is_active, u.ban_reason, u.banned_at = True, None, None
    u.failed_attempts, u.locked_until = 0, None
    db.commit()
    return admin_user_out(u)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    u = _get_other_user(user_id, me, db, "delete")
    # Courses reference their instructor without ON DELETE; detach them first.
    db.execute(update(Course).where(Course.instructor_id == u.id).values(instructor_id=None))
    db.delete(u)
    db.commit()
    return {"ok": True}


def _check_password(body: UserIn):
    problem = password_problem(body.password, name=body.name, email=body.email, student_id=body.student_id)
    if problem:
        raise HTTPException(422, problem)


def _check_user(body: UserIn, db: Session, own_id: int | None = None):
    if body.role not in ROLES:
        raise HTTPException(422, "Unknown role")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", body.email):
        raise HTTPException(422, "Invalid email")
    if body.student_id and not re.fullmatch(r"\d{9}", body.student_id):
        raise HTTPException(422, "Student ID must be 9 digits")
    clash = db.scalar(select(User).where(func.lower(User.email) == body.email.lower().strip()))
    if clash and clash.id != own_id:
        raise HTTPException(409, "Email already in use")
    if body.student_id:
        clash = db.scalar(select(User).where(User.student_id == body.student_id))
        if clash and clash.id != own_id:
            raise HTTPException(409, "Student ID already in use")


# ------------------------------------------------------------------ topics

class TopicIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=80)
    color: str = Field(default="#8b5cff", pattern=r"^#[0-9a-fA-F]{6}$")
    keywords: list[str] = Field(default_factory=list, max_length=80)
    is_active: bool = True


def topic_out(t: TopicCategory) -> dict:
    return {"id": t.id, "name": t.name, "color": t.color, "keywords": t.keywords, "is_active": t.is_active}


@router.get("/topics")
def list_topics(db: Session = Depends(get_db)):
    return [topic_out(t) for t in db.scalars(select(TopicCategory).order_by(TopicCategory.name))]


@router.post("/topics")
def create_topic(body: TopicIn, db: Session = Depends(get_db)):
    _assert_topic_name_available(db, body.name)
    t = TopicCategory(name=body.name, color=body.color,
                      keywords=_topic_keywords(body), is_active=body.is_active)
    db.add(t)
    _commit_topic(db)
    return topic_out(t)


@router.put("/topics/{topic_id}")
def update_topic(topic_id: int, body: TopicIn, db: Session = Depends(get_db)):
    t = db.get(TopicCategory, topic_id, with_for_update=True)
    if not t:
        raise HTTPException(404, "Topic not found")
    _assert_topic_name_available(db, body.name, t.id)
    old = t.name
    t.name, t.color, t.keywords, t.is_active = body.name, body.color, _topic_keywords(body), body.is_active
    if old != body.name:
        _rename_topic(db, old, body.name)
    _commit_topic(db)
    return topic_out(t)


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    t = db.get(TopicCategory, topic_id)
    if not t:
        raise HTTPException(404, "Topic not found")
    db.delete(t)
    db.commit()
    return {"ok": True, "hint": "Run 'Re-analyze feedback' to update existing records."}


def _assert_topic_name_available(db: Session, name: str, exclude_id: int | None = None):
    stmt = select(TopicCategory.id).where(func.lower(TopicCategory.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(TopicCategory.id != exclude_id)
    if db.scalar(stmt.limit(1)) is not None:
        raise HTTPException(409, "A topic with this name exists")


def _topic_keywords(body: TopicIn) -> list[str]:
    words = list(dict.fromkeys(" ".join(word.lower().split()) for word in body.keywords if word.strip()))
    if any(len(word) > 80 for word in words):
        raise HTTPException(422, "Each keyword or phrase must be at most 80 characters")
    if body.is_active and not words:
        raise HTTPException(422, "Add a keyword or phrase for an active topic")
    return words


def _commit_topic(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A topic with this name exists")


def _rename_topic(db: Session, old: str, new: str):
    for fb in db.scalars(select(Feedback)).yield_per(500):
        if old in (fb.topics or []):
            fb.topics = list(dict.fromkeys(new if t == old else t for t in fb.topics))
        if old in (fb.aspects or {}):
            aspects = dict(fb.aspects)
            tone = aspects.pop(old)
            aspects.setdefault(new, tone)
            fb.aspects = aspects
    db.execute(update(Action).where(Action.topic == old).values(topic=new))
    db.execute(update(Alert).where(Alert.top_topic == old).values(top_topic=new))


# ------------------------------------------------------------------ analysis correction

Tone = Literal["positive", "neutral", "negative"]


class CorrectionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    sentiment: Tone | None = None
    topics: list[str] | None = Field(default=None, max_length=80)
    aspects: dict[str, Tone] | None = Field(default=None, max_length=80)
    reason: str = Field(default="", max_length=300)


@router.patch("/feedback/{fb_id}/analysis")
def correct(fb_id: int, body: CorrectionIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    fb = db.get(Feedback, fb_id, with_for_update=True)
    if not fb:
        raise HTTPException(404, "Feedback not found")
    before = {"sentiment": fb.sentiment, "topics": fb.topics or [], "aspects": fb.aspects or {}}
    sentiment = body.sentiment or fb.sentiment
    topics = list(dict.fromkeys(body.topics if body.topics is not None else before["topics"]))
    if body.topics is not None:
        added = set(topics) - set(before["topics"])
        active = set(db.scalars(select(TopicCategory.name).where(TopicCategory.is_active.is_(True)))) if added else set()
        if added - active:
            raise HTTPException(422, "Choose an active topic category")
    if set(body.aspects or {}) - set(topics):
        raise HTTPException(422, "Assign sentiment only to selected topics")
    if body.aspects is not None or body.topics is not None:
        aspects = {topic: (body.aspects or {}).get(topic, before["aspects"].get(topic, sentiment))
                   for topic in topics}
    else:
        aspects = before["aspects"]
    after = {"sentiment": sentiment, "topics": topics, "aspects": aspects}
    if before != after:
        fb.sentiment, fb.topics, fb.aspects = sentiment, topics, aspects
        if label_for(fb.sentiment_score) != sentiment:
            fb.sentiment_score = {"positive": 0.6, "neutral": 0.0, "negative": -0.6}[sentiment]
        fb.is_corrected = True
        db.add(AnalysisCorrection(feedback_id=fb.id, corrected_by=user.id, before=before, after=after, reason=body.reason))
        db.commit()
    return {"id": fb.id, **after, "is_corrected": fb.is_corrected}


# ------------------------------------------------------------------ catalogue

class CourseIn(BaseModel):
    code: str = Field(min_length=2, max_length=24)
    title: str = Field(min_length=2, max_length=200)
    department_id: int
    instructor_id: int | None = None


class ServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category: str = "General"


@router.get("/catalogue")
def catalogue(db: Session = Depends(get_db)):
    return {
        "departments": [{"id": d.id, "code": d.code, "name": d.name}
                        for d in db.scalars(select(Department).order_by(Department.name))],
        "courses": [{"id": c.id, "code": c.code, "title": c.title, "department_id": c.department_id,
                     "department": c.department.name, "instructor_id": c.instructor_id,
                     "instructor": c.instructor.name if c.instructor else None}
                    for c in db.scalars(select(Course).order_by(Course.code))],
        "services": [{"id": s.id, "name": s.name, "category": s.category}
                     for s in db.scalars(select(Service).order_by(Service.name))],
        "faculty": [{"id": u.id, "name": u.name}
                    for u in db.scalars(select(User).where(User.role == "faculty").order_by(User.name))],
    }


@router.post("/courses")
def create_course(body: CourseIn, db: Session = Depends(get_db)):
    if db.scalar(select(Course).where(func.lower(Course.code) == body.code.lower())):
        raise HTTPException(409, "Course code already exists")
    if not db.get(Department, body.department_id):
        raise HTTPException(422, "Unknown department")
    c = Course(code=body.code.strip().upper(), title=body.title.strip(),
               department_id=body.department_id, instructor_id=body.instructor_id)
    db.add(c)
    db.commit()
    return {"id": c.id}


@router.post("/services")
def create_service(body: ServiceIn, db: Session = Depends(get_db)):
    if db.scalar(select(Service).where(func.lower(Service.name) == body.name.lower())):
        raise HTTPException(409, "Service already exists")
    s = Service(name=body.name.strip(), category=body.category.strip() or "General")
    db.add(s)
    db.commit()
    return {"id": s.id}
