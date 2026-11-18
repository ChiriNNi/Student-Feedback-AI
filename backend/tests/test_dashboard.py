import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Course, Department, Faculty, Feedback, Service, User
from app.routers.analytics import filters_dep, meta, overview
from app.services import Filters


class DashboardTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.db = Session(engine)
        self.addCleanup(self.db.close)
        self.faculty = Faculty(code="SCI", name="Science")
        self.department = Department(code="ENG", name="Engineering", faculty=self.faculty)
        self.sibling = Department(code="MATH", name="Mathematics", faculty=self.faculty)
        self.other = Department(code="ART", name="Arts", faculty=Faculty(code="HUM", name="Humanities"))
        self.teacher = self.user("faculty", self.department)
        self.manager = self.user("manager", self.department)
        self.admin = self.user("admin", None)
        self.course = Course(code="ENG101", title="Engineering", department=self.department,
                             instructor=self.teacher)
        self.other_course = Course(code="ART101", title="Arts", department=self.other)
        self.service = Service(name="Library")
        self.sibling_course = Course(code="MATH101", title="Mathematics", department=self.sibling)
        self.db.add_all([self.course, self.other_course, self.sibling_course, self.service])
        self.db.flush()

    def user(self, role, department):
        user = User(role=role, email=f"{role}@example.edu", name=role,
                    password_hash="fixture", department=department)
        self.db.add(user)
        return user

    def feedback(self, course=None, semester="Fall 2026", **values):
        self.db.add(Feedback(
            kind="course" if course else "service", semester=semester,
            course=course, department=course.department if course else None,
            service=None if course else self.service, text="", **values,
        ))
        self.db.flush()

    def test_aggregates_persisted_ratings_and_topics_with_role_scope(self):
        self.feedback(self.course, rating=4, ratings={"1": 3, "2": 4},
                      sentiment="positive", confidence=0.8, topics=["Workload", "Workload"])
        self.feedback(self.course, rating=2)
        self.feedback(self.other_course, rating=5, sentiment="negative", confidence=0.8)
        self.feedback(rating=5, sentiment="neutral", confidence=0.8)

        result = overview(Filters(), self.teacher, self.db)
        self.assertEqual((result["total"], result["rated"], result["avg_rating"]), (2, 2, 2.75))
        self.assertEqual((result["analyzed"], result["neutral"], result["positive_share"]), (1, 0, 1))
        self.assertEqual(result["top_topics"], [{"topic": "Workload", "total": 1}])
        self.assertEqual(overview(Filters(), self.manager, self.db)["total"], 3)
        self.assertEqual(overview(Filters(), self.admin, self.db)["total"], 4)

    def test_empty_overview(self):
        result = overview(Filters(), self.teacher, self.db)
        self.assertEqual(result["total"], 0)
        self.assertIsNone(result["avg_rating"])
        self.assertEqual(result["top_topics"], [])


    def test_faculty_and_department_are_distinct_filters(self):
        self.feedback(self.course, semester="Spring 2026")
        self.feedback(self.sibling_course)
        self.feedback(self.other_course)
        self.feedback()
        faculty = filters_dep(self.admin, self.db, faculty_id=self.faculty.id)
        self.assertEqual(overview(faculty, self.admin, self.db)["total"], 2)
        specific = filters_dep(self.admin, self.db, faculty_id=self.faculty.id,
                               department_id=self.department.id, instructor_id=self.teacher.id,
                               course_id=self.course.id, semester="Fall 2026")
        self.assertEqual(overview(specific, self.admin, self.db)["total"], 0)

    def test_options_and_filter_validation_respect_staff_scope(self):
        result = meta(self.manager, self.db)
        self.assertEqual([f["id"] for f in result["faculties"]], [self.faculty.id])
        self.assertEqual([d["id"] for d in result["departments"]], [self.department.id])
        self.assertEqual([c["id"] for c in result["courses"]], [self.course.id])
        self.assertEqual(meta(self.teacher, self.db)["services"], [])
        invalid_filters = [
            (self.manager, {"course_id": self.sibling_course.id}),
            (self.manager, {"faculty_id": self.other.faculty_id}),
            (self.teacher, {"service_id": self.service.id}),
            (self.admin, {"semester": "Winter 1900"}),
            (self.admin, {"course_id": self.other_course.id, "faculty_id": self.faculty.id}),
            (self.admin, {"course_id": self.other_course.id, "instructor_id": self.teacher.id}),
        ]
        for user, selection in invalid_filters:
            with self.subTest(role=user.role, selection=selection):
                with self.assertRaises(HTTPException) as rejection:
                    filters_dep(user, self.db, **selection)
                self.assertEqual(rejection.exception.status_code, 422)
