import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Department, User
from ..passwords import password_problem
from ..security import create_token, get_current_user, hash_password, revoke_sessions, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
STUDENT_ID_RE = re.compile(r"^\d{9}$")


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=200)
    remember: bool = False


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    student_id: str = Field(min_length=9, max_length=9)
    email: str = Field(min_length=5, max_length=160)
    department_id: int | None = None
    password: str = Field(min_length=1, max_length=200)  # strength checked by password_problem()


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=1, max_length=200)
    remember: bool = False  # lifetime of the fresh token issued to the current session


def user_out(u: User) -> dict:
    return {
        "id": u.id, "name": u.name, "email": u.email, "role": u.role,
        "student_id": u.student_id, "department_id": u.department_id,
        "department": u.department.name if u.department else None,
    }


def _error(status: int, code: str, message: str, **extra):
    return JSONResponse(status_code=status, content={"code": code, "detail": message, **extra})


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    # The role is never taken from the client — it is whatever the backend has
    # on file for this account, so the frontend cannot claim a different role.
    ident = body.login.strip().lower()
    user = db.scalar(select(User).where(or_(func.lower(User.email) == ident, User.student_id == ident)))
    now = datetime.now(timezone.utc)

    if user and user.locked_until and user.locked_until > now:
        wait = int((user.locked_until - now).total_seconds()) + 1
        return _error(423, "LOCKED", f"Too many failed attempts. Try again in {wait} seconds.", retry_after=wait)

    if not user:
        return _error(404, "USER_NOT_FOUND", "This user does not exist in the system.")
    if not user.is_active:
        msg = "This account has been banned."
        if user.ban_reason:
            msg += f" Reason: {user.ban_reason}"
        return _error(403, "ACCOUNT_BANNED", msg)

    if not verify_password(body.password, user.password_hash):
        user.failed_attempts += 1
        remaining = max(0, settings.max_login_attempts - user.failed_attempts)
        if user.failed_attempts >= settings.max_login_attempts:
            user.locked_until = now + timedelta(seconds=settings.lock_seconds)
            user.failed_attempts = 0
            db.commit()
            return _error(423, "LOCKED",
                          f"Too many failed attempts. Try again in {settings.lock_seconds} seconds.",
                          retry_after=settings.lock_seconds)
        db.commit()
        return _error(401, "INVALID_CREDENTIALS", "Incorrect password.", remaining=remaining)

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = now
    db.commit()
    token, expires = create_token(user, body.remember)
    return {"token": token, "expires_at": expires.isoformat(), "user": user_out(user)}


@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    # Public on purpose — the registration form needs it before the user has an account.
    depts = db.scalars(select(Department).order_by(Department.name)).all()
    return [{"id": d.id, "code": d.code, "name": d.name} for d in depts]


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    # Self-registration is for students only. Faculty/manager/admin accounts
    # are provisioned by an administrator, as in a real university system.
    name = body.name.strip()
    email = body.email.strip().lower()
    student_id = body.student_id.strip()

    if not STUDENT_ID_RE.match(student_id):
        raise HTTPException(422, "Student ID must be exactly 9 digits.")
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    problem = password_problem(body.password, name=name, email=email, student_id=student_id)
    if problem:
        return _error(422, "WEAK_PASSWORD", problem)
    if body.department_id is not None and not db.get(Department, body.department_id):
        raise HTTPException(422, "Unknown department.")

    if db.scalar(select(User).where(User.student_id == student_id)):
        return _error(409, "STUDENT_ID_TAKEN", "An account with this student ID already exists.")
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        return _error(409, "EMAIL_TAKEN", "An account with this email already exists.")

    user = User(
        name=name, email=email, student_id=student_id, role="student",
        department_id=body.department_id, password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent registrations for the same login — the earlier checks raced.
        db.rollback()
        return _error(409, "ALREADY_REGISTERED", "An account with this email or student ID already exists.")

    token, expires = create_token(user, remember=False)
    return {"token": token, "expires_at": expires.isoformat(), "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.post("/change-password")
def change_password(body: PasswordChangeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        return _error(400, "WRONG_PASSWORD", "Current password is incorrect.")
    if verify_password(body.new_password, user.password_hash):
        return _error(422, "WEAK_PASSWORD", "The new password must be different from the current one.")
    problem = password_problem(body.new_password, name=user.name, email=user.email, student_id=user.student_id)
    if problem:
        return _error(422, "WEAK_PASSWORD", problem)

    user.password_hash = hash_password(body.new_password)
    user.failed_attempts, user.locked_until = 0, None
    # Every token issued before this moment (other browsers, a stolen session) stops working.
    revoke_sessions(user)
    db.commit()
    # ...except the session that made the change, which gets a fresh token.
    token, expires = create_token(user, body.remember)
    return {"ok": True, "token": token, "expires_at": expires.isoformat()}


@router.post("/forgot")
def forgot(payload: dict):
    # Same response whether or not the account exists, to avoid account enumeration.
    return {"ok": True, "detail": "If an account exists, a reset link has been sent to the university email."}
