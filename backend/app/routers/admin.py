import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ROLES, Course, Department, Feedback, Service, TopicCategory, User
from ..security import admin_only, get_current_user, hash_password
from ..services import invalidate_topics
from .auth import user_out

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_only)])


# ------------------------------------------------------------------ users

class UserIn(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    name: str = Field(min_length=2, max_length=160)
    role: str
    student_id: str | None = None
    department_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)
    is_active: bool = True


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.role, User.name)).all()
    return [{**user_out(u), "is_active": u.is_active,
             "last_login": u.last_login.isoformat() if u.last_login else None} for u in users]


@router.post("/users")
def create_user(body: UserIn, db: Session = Depends(get_db)):
    _check_user(body, db)
    if not body.password:
        raise HTTPException(422, "Password is required for new users")
    u = User(email=body.email.lower().strip(), name=body.name.strip(), role=body.role,
             student_id=body.student_id or None, department_id=body.department_id,
             password_hash=hash_password(body.password), is_active=body.is_active)
    db.add(u)
    db.commit()
    return user_out(u)


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserIn, db: Session = Depends(get_db),
                me: User = Depends(get_current_user)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    _check_user(body, db, u.id)
    if u.id == me.id and (body.role != "admin" or not body.is_active):
        raise HTTPException(400, "You cannot remove your own admin access")
    u.email, u.name, u.role = body.email.lower().strip(), body.name.strip(), body.role
    u.student_id, u.department_id, u.is_active = body.student_id or None, body.department_id, body.is_active
    if body.password:
        u.password_hash = hash_password(body.password)
        u.failed_attempts, u.locked_until = 0, None
    db.commit()
    return user_out(u)


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
    name: str = Field(min_length=2, max_length=80)
    color: str = Field(default="#8b5cff", pattern=r"^#[0-9a-fA-F]{6}$")
    keywords: list[str] = []
    is_active: bool = True


def topic_out(t: TopicCategory) -> dict:
    return {"id": t.id, "name": t.name, "color": t.color, "keywords": t.keywords, "is_active": t.is_active}


@router.get("/topics")
def list_topics(db: Session = Depends(get_db)):
    return [topic_out(t) for t in db.scalars(select(TopicCategory).order_by(TopicCategory.name))]


@router.post("/topics")
def create_topic(body: TopicIn, db: Session = Depends(get_db)):
    if db.scalar(select(TopicCategory).where(func.lower(TopicCategory.name) == body.name.lower())):
        raise HTTPException(409, "A topic with this name exists")
    t = TopicCategory(name=body.name.strip(), color=body.color,
                      keywords=_clean_kw(body.keywords), is_active=body.is_active)
    db.add(t)
    db.commit()
    invalidate_topics()
    return topic_out(t)


@router.put("/topics/{topic_id}")
def update_topic(topic_id: int, body: TopicIn, db: Session = Depends(get_db)):
    t = db.get(TopicCategory, topic_id)
    if not t:
        raise HTTPException(404, "Topic not found")
    old = t.name
    t.name, t.color, t.keywords, t.is_active = body.name.strip(), body.color, _clean_kw(body.keywords), body.is_active
    db.commit()
    if old != t.name:
        _rename_topic(db, old, t.name)
    invalidate_topics()
    return topic_out(t)


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    t = db.get(TopicCategory, topic_id)
    if not t:
        raise HTTPException(404, "Topic not found")
    db.delete(t)
    db.commit()
    invalidate_topics()
    return {"ok": True, "hint": "Run 'Re-analyze feedback' to update existing records."}


def _clean_kw(words: list[str]) -> list[str]:
    seen, out = set(), []
    for w in words:
        w = w.strip().lower()
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def _rename_topic(db: Session, old: str, new: str):
    for fb in db.scalars(select(Feedback)).yield_per(500):
        if old in (fb.topics or []):
            fb.topics = [new if t == old else t for t in fb.topics]
            fb.aspects = {(new if k == old else k): v for k, v in (fb.aspects or {}).items()}
    db.commit()


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
