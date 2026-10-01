"""Creates demo departments and one user per role, with a fixed demo password.

Scope note: this project currently only needs the login flow to be fully real
(backend + database), so seeding is intentionally minimal — no courses,
surveys or generated feedback. The models for those still exist (kept for
future work) but nothing populates them here.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Department, User
from .security import hash_password

log = logging.getLogger("pulse.seed")

DEPARTMENTS = [
    ("ENS", "Faculty of Engineering and Natural Sciences"),
    ("BS", "SDU Business School"),
    ("EH", "Faculty of Education and Humanities"),
    ("LSS", "Faculty of Law and Social Sciences"),
]

# (email or None, student_id or None, name, role, department code or None)
DEMO_USERS = [
    ("240103083@stu.sdu.edu.kz", "240103083", "Demo Student", "student", "ENS"),
    ("faculty@sdu.edu.kz", None, "Dr. Aigerim Nurlanovna", "faculty", "ENS"),
    ("manager@sdu.edu.kz", None, "Quality Assurance Manager", "manager", None),
    ("admin@sdu.edu.kz", None, "System Administrator", "admin", None),
]


def seed(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        return
    log.info("Seeding demo departments and users...")

    depts = {code: Department(code=code, name=name) for code, name in DEPARTMENTS}
    db.add_all(depts.values())
    db.flush()

    pw = hash_password(settings.demo_password)
    for email, student_id, name, role, dept in DEMO_USERS:
        db.add(User(
            email=email, student_id=student_id, name=name, role=role,
            password_hash=pw, department_id=depts[dept].id if dept else None,
        ))
    db.commit()
    log.info("Seeded %d departments and %d demo users", len(depts), len(DEMO_USERS))
