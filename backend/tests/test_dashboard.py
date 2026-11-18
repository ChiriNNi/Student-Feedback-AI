import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Course, Department, Feedback, Service, User
from app.routers.analytics import overview
from app.services import Filters


class DashboardTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        self.db = Session(engine)
        self.addCleanup(self.db.close)
        self.department = Department(code="ENG", name="Engineering")
        self.other = Department(code="ART", name="Arts")
        self.teacher = self.user("faculty", self.department)
        self.manager = self.user("manager", self.department)
        self.admin = self.user("admin", None)
        self.course = Course(code="ENG101", title="Engineering", department=self.department,
                             instructor=self.teacher)
        self.other_course = Course(code="ART101", title="Arts", department=self.other)
        self.service = Service(name="Library")
        self.db.add_all([self.course, self.other_course, self.service])
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
