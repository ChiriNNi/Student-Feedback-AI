import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import AnalysisCorrection, Course, Department, Feedback, SubmissionReceipt, Survey, SurveyQuestion, User
from app.routers.actions import ActionIn, ActionStatusIn, change_action_status, create_action, list_actions
from app.routers.admin import CorrectionIn, TopicIn, correct, create_topic, update_topic
from app.routers.analytics import overview
from app.routers.evaluations import SubmitIn, open_forms, submit
from app.routers.surveys import QuestionIn, StatusIn, SurveyIn, change_status, create_survey, list_surveys, update_survey
from app.services import Filters


class Sprint6Workflows(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.addCleanup(engine.dispose)
        self.db = Session(engine)
        self.addCleanup(self.db.close)
        self.own = Department(code="ENS", name="Engineering")
        self.other = Department(code="LAW", name="Law")
        self.student = self.user("student", self.own)
        self.admin = self.user("admin")
        self.manager = self.user("manager", self.own)
        self.other_manager = self.user("manager", self.other, "-other")
        self.course = Course(code="ENS101", title="Intro to Engineering", department=self.own)
        self.other_course = Course(code="LAW101", title="Intro to Law", department=self.other)
        self.default_question = SurveyQuestion(kind="course", label="Overall", text="Overall quality")
        self.legacy = Survey(title="Legacy course evaluation", kind="course", semester="Fall 2026", status="open")
        self.db.add_all([self.course, self.other_course, self.default_question, self.legacy])
        self.db.commit()

    def user(self, role, department=None, suffix=""):
        user = User(email=f"{role}{suffix}@example.edu", name=f"{role}{suffix}", role=role,
                    password_hash="fixture", department=department)
        self.db.add(user)
        return user

    def form(self, kind="course", questions=None):
        return SurveyIn(title="New feedback form", kind=kind, semester=" spring  2027 ",
                        questions=questions if questions is not None else [QuestionIn(label="Labs", text="Labs are useful")])

    def add_feedback(self, course, topic):
        self.db.add(Feedback(kind="course", semester="Fall 2026", course=course, department=course.department,
                             text="an anonymous comment", rating=2, sentiment="negative", confidence=.8,
                             topics=[topic], aspects={topic: "negative"}))
        self.db.flush()

    def test_custom_form_lifecycle_and_legacy_questions(self):
        draft = create_survey(self.form(), self.db)
        self.assertEqual(draft["semester"], "Spring 2027")
        self.assertEqual(draft["status"], "draft")
        self.assertEqual([form["id"] for form in open_forms(self.student, self.db)], [self.legacy.id])
        edit = self.form(questions=[QuestionIn(label="Workload", text="Lab workload was manageable")])
        saved = update_survey(draft["id"], edit, self.db)
        question_id = saved["questions"][0]["id"]
        change_status(draft["id"], StatusIn(status="open"), self.db)
        forms = {form["id"]: form for form in open_forms(self.student, self.db)}
        self.assertEqual(forms[self.legacy.id]["questions"][0]["id"], self.default_question.id)
        self.assertEqual(forms[draft["id"]]["questions"][0]["id"], question_id)
        self.assertNotEqual(question_id, self.default_question.id)
        with self.assertRaises(HTTPException) as error:
            submit(draft["id"], SubmitIn(course_id=self.course.id, ratings={self.default_question.id: 4}), self.student, self.db)
        self.assertEqual(error.exception.status_code, 422)
        submit(draft["id"], SubmitIn(course_id=self.course.id, ratings={question_id: 4}), self.student, self.db)
        self.assertEqual(self.db.scalar(select(Feedback)).ratings, {str(question_id): 4})
        self.assertEqual(self.db.scalar(select(SubmissionReceipt)).target_key, f"course:{self.course.id}")
        self.assertEqual(change_status(draft["id"], StatusIn(status="closed"), self.db)["responses"], 1)
        with self.assertRaises(HTTPException) as error:
            update_survey(draft["id"], self.form(), self.db)
        self.assertEqual(error.exception.status_code, 409)
        with self.assertRaises(HTTPException) as error:
            submit(draft["id"], SubmitIn(course_id=self.course.id, ratings={question_id: 4}), self.student, self.db)
        self.assertEqual(error.exception.status_code, 404)
        self.assertNotIn(draft["id"], [form["id"] for form in open_forms(self.student, self.db)])
        change_status(draft["id"], StatusIn(status="open"), self.db)
        published = next(form for form in open_forms(self.student, self.db) if form["id"] == draft["id"])
        self.assertTrue(published["targets"][0]["done"])

    def test_general_survey_accepts_anonymous_written_response(self):
        draft = create_survey(self.form("survey", []), self.db)
        change_status(draft["id"], StatusIn(status="open"), self.db)
        form = next(form for form in open_forms(self.student, self.db) if form["id"] == draft["id"])
        self.assertTrue(form["comment_required"])
        with self.assertRaises(HTTPException):
            submit(draft["id"], SubmitIn(ratings={}), self.student, self.db)
        returned = submit(draft["id"], SubmitIn(ratings={}, comment="Contact me at test@example.edu"), self.student, self.db)
        answer = self.db.scalar(select(Feedback))
        self.assertIsNone(answer.rating)
        self.assertNotIn("test@example.edu", returned["comment"])
        self.assertEqual(answer.department_id, self.own.id)

    def test_demo_archive_cannot_be_published_as_a_student_form(self):
        archive = Survey(title="Demo history", kind="survey", semester="Fall 2025", status="closed", is_demo_archive=True)
        self.db.add(archive)
        self.db.commit()
        self.assertNotIn(archive.id, [item["id"] for item in list_surveys(self.db)["items"]])
        with self.assertRaises(HTTPException) as error:
            change_status(archive.id, StatusIn(status="open"), self.db)
        self.assertEqual(error.exception.status_code, 404)

    def test_taxonomy_rename_applies_to_history_actions_and_new_analysis(self):
        topic = create_topic(TopicIn(name="Lab access", keywords=["laboratory booking"]), self.db)
        for _ in range(3):
            self.add_feedback(self.course, topic["name"])
        action = create_action(ActionIn(title="Extend lab access", topic=topic["name"], course_id=self.course.id),
                               self.manager, self.db)
        updated = update_topic(topic["id"], TopicIn(name="Lab availability", keywords=["laboratory booking"]), self.db)
        self.assertEqual(list_actions(self.manager, self.db)[0]["id"], action["id"])
        self.assertEqual(list_actions(self.manager, self.db)[0]["topic"], updated["name"])
        self.assertEqual(overview(Filters(), self.manager, self.db)["top_topics"][0]["topic"], updated["name"])
        submit(self.legacy.id, SubmitIn(course_id=self.course.id, ratings={self.default_question.id: 4},
              comment="Laboratory booking was excellent."), self.student, self.db)
        response = self.db.scalar(select(Feedback).order_by(Feedback.id.desc()).limit(1))
        self.assertIn(updated["name"], response.topics)
        with self.assertRaises(HTTPException) as error:
            create_topic(TopicIn(name=" LAB availability ", keywords=["access"]), self.db)
        self.assertEqual(error.exception.status_code, 409)

    def test_correction_updates_dashboard_and_keeps_an_audit_entry(self):
        create_topic(TopicIn(name="Equipment", keywords=["equipment"]), self.db)
        self.add_feedback(self.course, "Raw label")
        feedback = self.db.scalar(select(Feedback))
        correction = CorrectionIn(sentiment="positive", topics=["Equipment"], aspects={"Equipment": "positive"},
                                  reason="The author praised the equipment")
        updated = correct(feedback.id, correction, self.admin, self.db)
        self.assertTrue(updated["is_corrected"])
        self.assertEqual(feedback.text, "an anonymous comment")
        dashboard = overview(Filters(), self.manager, self.db)
        self.assertEqual(dashboard["positive"], 1)
        self.assertEqual(dashboard["top_topics"], [{"topic": "Equipment", "total": 1}])
        audit = self.db.scalar(select(AnalysisCorrection))
        self.assertEqual(audit.corrected_by, self.admin.id)
        self.assertEqual(audit.before["sentiment"], "negative")
        self.assertEqual(audit.after["aspects"], {"Equipment": "positive"})
        correct(feedback.id, correction, self.admin, self.db)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(AnalysisCorrection)), 1)
        with self.assertRaises(HTTPException) as error:
            correct(feedback.id, CorrectionIn(topics=["Unknown"]), self.admin, self.db)
        self.assertEqual(error.exception.status_code, 422)

    def test_action_is_linked_and_scoped_and_status_is_saved(self):
        for _ in range(3):
            self.add_feedback(self.course, "Workload")
        action = create_action(ActionIn(title="Stagger deadlines", course_id=self.course.id, topic="Workload"),
                               self.manager, self.db)
        self.assertEqual(action["topic"], "Workload")
        self.assertEqual(action["department_id"], self.own.id)
        self.assertEqual(list_actions(self.other_manager, self.db), [])
        with self.assertRaises(HTTPException) as error:
            change_action_status(action["id"], ActionStatusIn(status="done"), self.other_manager, self.db)
        self.assertEqual(error.exception.status_code, 404)
        with self.assertRaises(HTTPException) as error:
            create_action(ActionIn(title="Unrelated action", course_id=self.other_course.id, topic="Workload"),
                          self.manager, self.db)
        self.assertEqual(error.exception.status_code, 422)
        with self.assertRaises(HTTPException):
            create_action(ActionIn(title="Unlinked problem", course_id=self.course.id, topic="Not detected"),
                          self.manager, self.db)
        change_action_status(action["id"], ActionStatusIn(status="in_progress"), self.manager, self.db)
        self.assertEqual(list_actions(self.manager, self.db)[0]["status"], "in_progress")
        change_action_status(action["id"], ActionStatusIn(status="done"), self.manager, self.db)
        self.assertEqual(list_actions(self.manager, self.db)[0]["status"], "done")
