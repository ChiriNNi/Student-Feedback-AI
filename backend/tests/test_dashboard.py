import asyncio
import unittest
from io import BytesIO

from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Alert, Course, Department, Faculty, Feedback, Service, User
from app.routers.analytics import filters_dep, meta, overview, summary, trends
from app.routers.evaluations import responses
from app.routers.management import _report_rows, comparison
from app.routers.reports import summary_excel
from app.services import Filters, recompute_alerts


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


    def test_trends_sort_terms_and_distinguish_zero_mentions_from_missing_data(self):
        self.feedback(self.course, semester="Fall 2026", sentiment="negative",
                      confidence=0.8, topics=["Workload", "Workload", "semester"])
        self.feedback(self.course, semester="Fall 2026", sentiment="positive", confidence=0.8)
        self.feedback(self.course, semester="Fall 2026")
        self.feedback(self.course, semester="Spring 2025", sentiment="neutral", confidence=0.8)
        self.feedback(self.sibling_course, semester="Summer 2026", sentiment="positive",
                      confidence=0.8, topics=["Resources"])
        self.feedback(self.course, semester="Fall 2027")

        result = trends(Filters(course_id=self.course.id), self.manager, self.db)
        # The sibling course is outside the manager's scope.
        self.assertEqual([p["semester"] for p in result["series"]],
                         ["Spring 2025", "Fall 2026", "Fall 2027"])
        fall = result["series"][1]
        self.assertEqual((fall["total"], fall["analyzed"], fall["negative_share"]), (3, 2, 0.5))
        self.assertEqual([p["mentions"] for p in result["topic_series"]],
                         [{"Workload": 0, "semester": 0}, {"Workload": 1, "semester": 1}, None])

        result = trends(Filters(course_id=self.course.id), self.admin, self.db)
        self.assertEqual(result["series"][1]["semester"], "Summer 2026")
        self.assertEqual(result["series"][1]["total"], 0)
        self.assertIsNone(result["topic_series"][1]["mentions"])

    def test_alerts_keep_earlier_rises_and_their_detection_semesters(self):
        for semester, negative in (("Fall 2025", 1), ("Spring 2026", 7),
                                   ("Fall 2026", 7), ("Spring 2027", 7)):
            for index in range(8):
                self.feedback(semester=semester, sentiment="negative" if index < negative else "positive",
                              aspects={"Digital Resources": "negative"} if index < negative else {})
        self.assertEqual(recompute_alerts(self.db), 1)
        alert = self.db.scalars(select(Alert)).one()
        self.assertEqual((alert.previous_semester, alert.semester, alert.top_topic),
                         ("Fall 2025", "Spring 2026", "Digital Resources"))
        alert.is_read = True
        self.db.commit()
        self.assertEqual(recompute_alerts(self.db), 0)
        self.assertTrue(self.db.scalars(select(Alert)).one().is_read)

    def test_trends_honor_semester_and_empty_scope(self):
        self.feedback(self.course, semester="Spring 2026", confidence=0.8)
        self.feedback(self.course, semester="Fall 2026", confidence=0.8)
        result = trends(Filters(semester="Fall 2026"), self.teacher, self.db)
        self.assertEqual([p["semester"] for p in result["series"]], ["Fall 2026"])
        history = trends(Filters(semester="Fall 2026", course_id=self.course.id),
                         self.teacher, self.db, include_history=True)
        self.assertEqual([(p["semester"], p["total"]) for p in history["series"]],
                         [("Spring 2026", 1), ("Fall 2026", 1)])
        self.assertEqual(trends(Filters(course_id=self.other_course.id), self.admin, self.db)["series"], [])


    def test_summary_and_exports_use_unrounded_metrics_and_analyzed_responses(self):
        self.feedback(self.course, rating=4, ratings={"1": 3, "2": 4, "3": 4},
                      sentiment="positive", confidence=0.8)
        self.feedback(self.course, rating=2, sentiment="negative", confidence=0.8)
        self.feedback(self.course, sentiment="negative", confidence=0.8)
        self.feedback(self.course, sentiment="neutral")  # Stored default, without analysis.
        filters = Filters(course_id=self.course.id)
        board = overview(filters, self.teacher, self.db)
        narrative = summary(False, filters, self.teacher, self.db)
        self.assertAlmostEqual(board["avg_rating"], (11 / 3 + 2) / 2)
        self.assertEqual(narrative["avg_rating"], board["avg_rating"])
        self.assertEqual(narrative["analyzed"], 3)
        self.assertEqual(narrative["sentiment"], {"positive": 1, "neutral": 0, "negative": 2})
        self.assertEqual(board["positive_share"], 1 / 3)
        self.assertAlmostEqual(board["satisfaction_index"], -100 / 3)

        async def collect_export():
            export = summary_excel(filters, self.teacher, self.db)
            return b"".join([chunk async for chunk in export.body_iterator])

        workbook = load_workbook(BytesIO(asyncio.run(collect_export())))
        exported = {row[0]: row[1] for row in workbook["Overview"].values if len(row) > 1}
        self.assertAlmostEqual(exported["Average satisfaction /5"], board["avg_rating"])
        self.assertAlmostEqual(exported["Positive share"], board["positive_share"])
        self.assertAlmostEqual(exported["Net sentiment (pp)"], board["satisfaction_index"])
        _, report = _report_rows(self.db, self.manager, filters, "overview")
        self.assertAlmostEqual(dict(report)["Average satisfaction / 5"], board["avg_rating"])

    def test_summary_and_report_indicate_unavailable_sentiment(self):
        self.feedback(self.course, rating=4)
        filters = Filters(course_id=self.course.id)
        narrative = summary(False, filters, self.teacher, self.db)
        self.assertEqual(narrative["analyzed"], 0)
        self.assertIn("Sentiment analysis is unavailable", narrative["overview"])
        _, report = _report_rows(self.db, self.manager, filters, "trends")
        self.assertEqual(report[0][3:], [None, None, None])

    def test_management_exports_follow_dashboard_periods(self):
        self.feedback(self.course, semester="Fall 2025", rating=5)
        self.feedback(self.course, semester="Spring 2026", rating=3)
        self.feedback(self.course, semester="Fall 2026", rating=2)
        filters = Filters(semester="Spring 2026")

        _, trend_rows = _report_rows(self.db, self.manager, filters, "trends")
        self.assertEqual([row[0] for row in trend_rows], ["Spring 2026"])

        displayed = comparison("course", filters, self.manager, self.db)
        columns, rows = _report_rows(self.db, self.manager, filters, "compare_course")
        self.assertEqual(columns, ["Name", "Spring 2026 rating / 5", "Spring 2026 responses",
                                   "Fall 2025 rating / 5", "Fall 2025 responses"])
        item = displayed["items"][0]
        self.assertEqual(rows, [[item["name"], item["current"]["avg_rating"], item["current"]["total"],
                                 item["previous"]["avg_rating"], item["previous"]["total"]]])

    def test_explorer_uses_dashboard_scope_for_kind_and_empty_courses(self):
        self.feedback(self.course)
        self.feedback()
        for selection in ({"kind": "service"}, {"course_id": self.sibling_course.id}):
            filters = filters_dep(self.admin, self.db, **selection)
            dashboard = overview(filters, self.admin, self.db)
            explorer = responses(filters, self.admin, self.db)
            self.assertEqual(len(explorer["items"]), dashboard["total"])
            self.assertEqual(len(explorer["items"]), int(selection.get("kind") == "service"))
            self.assertTrue(all("user_id" not in item for item in explorer["items"]))

    def test_trends_order_winter_and_other_terms_across_years(self):
        chronological = ["Fall 2025", "Winter 2026", "Spring 2026", "Summer 2026",
                         "Fall 2026", "Winter 2027"]
        for term in reversed(chronological):
            self.feedback(self.course, semester=term, confidence=0.8)
        result = trends(Filters(), self.teacher, self.db)
        self.assertEqual([point["semester"] for point in result["series"]], chronological)
