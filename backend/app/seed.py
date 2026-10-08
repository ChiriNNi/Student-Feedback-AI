"""Creates demo departments, one user per role, and the catalogue the feedback forms need.

Each part is seeded independently and only when its table is empty, so a
database created by an earlier version picks up the newer parts on restart.
No feedback is generated — every response in the system comes from a real form.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Course, Department, Service, Survey, SurveyQuestion, User
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


# (code, title, department code, taught by the demo faculty account)
COURSES = [
    ("CSS 101", "Programming Fundamentals", "ENS", True),
    ("CSS 215", "Database Systems", "ENS", True),
    ("INF 318", "Software Engineering", "ENS", False),
    ("MAT 152", "Calculus II", "ENS", False),
    ("MGT 201", "Principles of Management", "BS", False),
    ("FIN 210", "Corporate Finance", "BS", False),
    ("ENG 105", "Academic English", "EH", False),
    ("PED 220", "Educational Psychology", "EH", False),
    ("LAW 110", "Introduction to Law", "LSS", False),
    ("POL 230", "Political Science", "LSS", False),
]

SERVICES = [
    ("Library", "Academic"),
    ("Dormitory", "Housing"),
    ("Cafeteria", "Food"),
    ("Sports Center", "Campus life"),
    ("IT Help Desk", "IT"),
    ("Registrar's Office", "Administration"),
    ("Career Center", "Career"),
]

# (kind, short label, statement rated 1-5)
QUESTIONS = [
    ("course", "Clarity", "The instructor explained the material clearly."),
    ("course", "Materials", "Course materials were useful and up to date."),
    ("course", "Workload", "The workload was reasonable for the credits."),
    ("course", "Assessment", "Assessment and grading were fair and transparent."),
    ("course", "Overall", "Overall, I am satisfied with this course."),
    ("service", "Staff", "Staff were helpful and polite."),
    ("service", "Availability", "The service was available when I needed it."),
    ("service", "Quality", "The quality of the service and facilities was good."),
    ("service", "Overall", "Overall, I am satisfied with this service."),
]

SEMESTER = "Fall 2026"
SURVEYS = [
    ("Fall 2026 Course Evaluation", "course",
     "Rate the courses you took this semester. Your answers are anonymous.",
     "What worked well in this course, and what should be improved?"),
    ("Fall 2026 Service Review", "service",
     "Tell service units how they are doing. Your answers are anonymous.",
     "What did you like about this service, and what should change?"),
]


def seed(db: Session) -> None:
    _seed_users(db)
    _seed_catalogue(db)


def _seed_users(db: Session) -> None:
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


def _seed_catalogue(db: Session) -> None:
    added = []
    if not db.scalar(select(Course).limit(1)):
        depts = {d.code: d.id for d in db.scalars(select(Department))}
        teacher = db.scalar(select(User).where(User.email == "faculty@sdu.edu.kz"))
        for code, title, dept, own in COURSES:
            if dept in depts:
                db.add(Course(code=code, title=title, department_id=depts[dept],
                              instructor_id=teacher.id if own and teacher else None))
        added.append("courses")
    if not db.scalar(select(Service).limit(1)):
        db.add_all(Service(name=n, category=c) for n, c in SERVICES)
        added.append("services")
    if not db.scalar(select(SurveyQuestion).limit(1)):
        db.add_all(SurveyQuestion(kind=k, label=l, text=t, position=i)
                   for i, (k, l, t) in enumerate(QUESTIONS))
        added.append("questions")
    if not db.scalar(select(Survey).limit(1)):
        db.add_all(Survey(title=t, kind=k, description=d, question=q, semester=SEMESTER, status="open")
                   for t, k, d, q in SURVEYS)
        added.append("surveys")
    if added:
        db.commit()
        log.info("Seeded %s", ", ".join(added))
