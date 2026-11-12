"""Creates a complete, presentation-ready local demo dataset.

Each part is seeded independently and only when its table is empty, so a
database created by an earlier version picks up the newer parts on restart.
Synthetic feedback is clearly marked with ``source=seed`` and is only created
when demo data is enabled and the feedback table is empty.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Course, Department, Feedback, Service, Survey, SurveyQuestion, TopicCategory, User
from .nlp.lexicons import DEFAULT_TOPICS
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
     "Rate the courses you took this semester.",
     "What worked well in this course, and what should be improved?"),
    ("Fall 2026 Service Review", "service",
     "Tell university services how they are doing.",
     "What did you like about this service, and what should change?"),
]

# (kind, course code or service name, ratings in question order, comment)
# The comments deliberately cover every Sprint 3 capability: three languages,
# mixed/aspect sentiment, multiple topics, and recurring negative problems.
DEMO_FEEDBACK = [
    ("course", "CSS 101", [4, 4, 4, 4, 4], "The instructor explains complex ideas very clearly and the lectures are engaging."),
    ("course", "CSS 215", [5, 4, 1, 3, 3], "The instructor was excellent, but the workload was terrible and deadlines were stressful."),
    ("course", "INF 318", [3, 3, 1, 2, 2], "Too many assignments every week and the workload is overwhelming."),
    ("course", "MAT 152", [3, 3, 1, 2, 2], "Homework takes too much time and deadlines overlap with other courses."),
    ("course", "MGT 201", [4, 4, 4, 4, 4], "The course content is relevant and the practical examples are useful."),
    ("course", "FIN 210", [3, 3, 3, 1, 2], "Grading criteria are unclear and the exam was unfair."),
    ("course", "ENG 105", [4, 4, 4, 4, 4], "Преподаватель очень понятно объясняет материал, лекции интересные."),
    ("course", "PED 220", [3, 3, 3, 3, 3], "The lectures were okay and the syllabus covers the standard topics."),
    ("course", "LAW 110", [3, 3, 3, 1, 2], "Бағалау критерийі түсініксіз, емтихан әділетсіз болды."),
    ("course", "POL 230", [4, 4, 4, 4, 4], "Everything is well organized and announcements come on time."),
    ("service", "Library", [3, 2, 2, 2], "There are not enough seats in the library during exams and weekend hours are limited."),
    ("service", "Dormitory", [3, 2, 1, 2], "В общежитии холодно, душ сломан и кухня грязная."),
    ("service", "Cafeteria", [3, 3, 1, 2], "Food prices in the cafeteria are too expensive and the lunch queue is very long."),
    ("service", "Sports Center", [4, 4, 4, 4], "The sports facilities are modern and the staff are friendly and helpful."),
    ("service", "IT Help Desk", [4, 2, 2, 2], "The Wi-Fi is very slow and the online portal keeps disconnecting."),
    ("service", "Registrar's Office", [2, 2, 2, 2], "The staff are rude and the waiting time is too long. There are long queues."),
    ("service", "Career Center", [4, 4, 4, 4], "Support staff solved my problem quickly and were very professional."),
    # Sprint 4 demo: repeated themes, suggestions and comments in all three languages
    ("course", "CSS 101", [5, 5, 3, 4, 5], "Great lectures, but please add more practice tasks before the midterm."),
    ("course", "CSS 101", [4, 4, 2, 3, 3], "Хотелось бы больше практических заданий, дедлайны слишком близко друг к другу."),
    ("course", "CSS 215", [4, 5, 2, 3, 4], "Мұғалім материалды түсінікті түсіндіреді, бірақ үй тапсырмасы тым көп."),
    ("course", "CSS 215", [3, 3, 2, 2, 2], "The exam questions did not match the lectures. It would be better to publish sample questions."),
    ("course", "INF 318", [4, 4, 3, 4, 4], "The team project is useful and the instructor gives clear feedback on our code."),
    ("course", "MAT 152", [2, 2, 1, 2, 2], "Lectures are too fast and the homework deadlines are stressful."),
    ("service", "IT Help Desk", [3, 2, 2, 2], "Wi-Fi in the dormitory does not work in the evening, please fix the internet."),
    ("service", "IT Help Desk", [3, 3, 2, 2], "Интернет в корпусе постоянно пропадает, портал не открывается."),
    ("service", "Library", [4, 4, 4, 4], "Кітапхана тыныш және ыңғайлы, бірақ демалыс күндері де ашық болуы керек."),
    ("service", "Library", [4, 3, 3, 3], "The library is quiet, but it would be nice to have more seats and longer opening hours."),
    ("service", "Cafeteria", [3, 3, 2, 2], "Асханада кезек өте ұзақ, тамақ қымбат."),
    ("service", "Cafeteria", [4, 4, 3, 4], "The food is tasty and fresh, but please add more vegetarian options."),
]


def seed(db: Session, *, include_demo: bool = True) -> None:
    if include_demo:
        _seed_users(db)
        _seed_catalogue(db)
    _seed_topics(db)
    if include_demo:
        _seed_feedback(db)
        _seed_demo_history(db)
    _backfill_sprint3(db)


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


def _seed_topics(db: Session) -> None:
    """Install the editable Sprint 3 taxonomy into new and upgraded databases."""
    if db.scalar(select(TopicCategory).limit(1)):
        return
    db.add_all(TopicCategory(**topic) for topic in DEFAULT_TOPICS)
    db.commit()
    log.info("Seeded %d topic categories", len(DEFAULT_TOPICS))


def _seed_feedback(db: Session) -> None:
    """Add analyzed sample responses to an otherwise empty demo database."""
    if db.scalar(select(Feedback.id).limit(1)):
        return

    from .services import analyze_into, get_matchers

    courses = {course.code: course for course in db.scalars(select(Course))}
    services = {service.name: service for service in db.scalars(select(Service))}
    surveys = {survey.kind: survey for survey in db.scalars(select(Survey))}
    questions = {
        kind: db.scalars(select(SurveyQuestion).where(SurveyQuestion.kind == kind)
                         .order_by(SurveyQuestion.position, SurveyQuestion.id)).all()
        for kind in ("course", "service")
    }
    matchers = get_matchers(db)
    added = 0

    for kind, target_name, values, comment in DEMO_FEEDBACK:
        target = courses.get(target_name) if kind == "course" else services.get(target_name)
        survey = surveys.get(kind)
        target_questions = questions[kind]
        if not target or not survey or len(values) != len(target_questions):
            log.warning("Skipping demo feedback for missing or incomplete target %s", target_name)
            continue

        ratings = {str(question.id): value for question, value in zip(target_questions, values)}
        feedback = Feedback(
            survey_id=survey.id,
            kind=kind,
            semester=survey.semester,
            course_id=target.id if kind == "course" else None,
            service_id=target.id if kind == "service" else None,
            department_id=target.department_id if kind == "course" else None,
            rating=round(sum(values) / len(values)),
            ratings=ratings,
            text="",
            source="seed",
        )
        analyze_into(feedback, comment, matchers)
        db.add(feedback)
        added += 1

    if added:
        db.commit()
        log.info("Seeded %d analyzed demo feedback rows", added)



def _seed_demo_history(db: Session) -> None:
    """Add three-period *labelled sample* comparisons to a DEMO database only.

    Existing student submissions are never changed; only new source='seed' rows
    are inserted. Each semester is checked independently (idempotent on restart).
    Production systems set SEED_DEMO_DATA=false to disable all demo seeding.
    """
    from .services import analyze_into, get_matchers

    if not db.scalar(select(Feedback.id).where(Feedback.source == "seed").limit(1)):
        return
    courses = {c.code: c for c in db.scalars(select(Course))}
    services = {v.name: v for v in db.scalars(select(Service))}
    questions = {kind: db.scalars(select(SurveyQuestion).where(SurveyQuestion.kind == kind)
                     .order_by(SurveyQuestion.position, SurveyQuestion.id)).all()
                 for kind in ("course", "service")}
    matchers = get_matchers(db)
    # Distinct historical distributions give the dashboard actual three-point demo trends.
    # IT Help Desk gets 12 responses per semester, so the negative spike has enough
    # samples for the existing alert rule (>= ALERT_MIN_FEEDBACK).
    focus = [
        ("service", "IT Help Desk"), ("service", "Library"),
        ("course", "CSS 101"), ("course", "CSS 215"),
    ]
    neutral = "The service is adequate and the team handled questions as expected."
    positive = "Support staff were very helpful and everything was easy to use."
    negative = "The internet connection keeps failing and students cannot access the online portal."
    teaching_good = "The lecturer explains clearly and the lessons are well organised."
    teaching_bad = "The teaching and deadlines were confusing and workload was too heavy."
    periods = ["Fall 2025", "Spring 2026", "Fall 2026"]
    for semester in periods:
        # Never duplicate demo additions on container restart.
        marker = db.scalar(select(Survey).where(Survey.title == f"Sprint 5 demo history — {semester}"))
        if marker:
            continue
        survey = Survey(title=f"Sprint 5 demo history — {semester}",
                        description="Synthetic sample dataset for semester comparisons only",
                        question="Demo history", semester=semester, kind="survey", status="closed")
        db.add(survey)
        db.flush()
        for kind, target_name in focus:
            target = courses.get(target_name) if kind == "course" else services.get(target_name)
            qs = questions[kind]
            if not target or not qs:
                continue
            for i in range(12):
                if kind == "service" and target_name == "IT Help Desk":
                    # sharp rise: 8% -> 17% -> 75% (approx), enough alert support
                    negative_count = {"Fall 2025": 1, "Spring 2026": 2, "Fall 2026": 9}[semester]
                    is_negative = i < negative_count
                elif semester == "Fall 2025":
                    is_negative = i < 4
                elif semester == "Spring 2026":
                    is_negative = i < 2
                else:
                    is_negative = i < 3
                score = 2 if is_negative else (4 if i % 4 else 3)
                ratings = {str(q.id): score for q in qs}
                comment = (teaching_bad if is_negative else teaching_good) if kind == "course" else (negative if is_negative else positive)
                fb = Feedback(survey_id=survey.id, kind=kind, semester=semester,
                              course_id=target.id if kind == "course" else None,
                              service_id=target.id if kind == "service" else None,
                              department_id=target.department_id if kind == "course" else None,
                              rating=score, ratings=ratings, text="", source="seed")
                analyze_into(fb, comment, matchers)
                db.add(fb)
        # Include one row per other course/service in both earlier semesters,
        # to make department/service comparisons useful without invented labels.
        if semester != "Fall 2026":
            focused_courses = {name for kind, name in focus if kind == "course"}
            focused_services = {name for kind, name in focus if kind == "service"}
            for kind, targets, excluded in (("course", courses, focused_courses), ("service", services, focused_services)):
                qs = questions[kind]
                for target_name, target in targets.items():
                    if target_name in excluded or not qs:
                        continue
                    score = 3 if semester == "Fall 2025" else 4
                    fb = Feedback(survey_id=survey.id, kind=kind, semester=semester,
                                  course_id=target.id if kind == "course" else None,
                                  service_id=target.id if kind == "service" else None,
                                  department_id=target.department_id if kind == "course" else None,
                                  rating=score, ratings={str(q.id): score for q in qs}, text="", source="seed")
                    analyze_into(fb, teaching_good if kind == "course" else neutral, matchers)
                    db.add(fb)
        db.commit()
        log.info("Seeded historical demo semester %s (source=seed)", semester)

def _backfill_sprint3(db: Session) -> None:
    """Analyze Sprint 2 rows once after an existing database is upgraded."""
    from .services import analyze_into, get_matchers

    rows = db.scalars(select(Feedback).where(Feedback.confidence == 0)).all()
    if not rows:
        return
    matchers = get_matchers(db)
    for feedback in rows:
        analyze_into(feedback, feedback.text, matchers)
    db.commit()
    log.info("Analyzed %d existing feedback rows for Sprint 3", len(rows))
