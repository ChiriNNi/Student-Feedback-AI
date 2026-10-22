import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    Course, Department, Feedback, SubmissionReceipt, Survey, SurveyQuestion, TopicCategory, User,
)
from app.nlp.lexicons import DEFAULT_TOPICS
from app.routers.evaluations import SubmitIn, submit
from app.services import invalidate_topics


class Sprint3SubmissionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        department = Department(code="ENS", name="Engineering")
        student = User(
            email="student@sdu.edu.kz", student_id="240103083", name="Demo Student",
            role="student", password_hash="test", department=department,
        )
        teacher = User(
            email="teacher@sdu.edu.kz", name="Dr. Aigerim Nurlanovna",
            role="faculty", password_hash="test", department=department,
        )
        course = Course(code="CSS 101", title="Programming Fundamentals",
                        department=department, instructor=teacher)
        survey = Survey(title="Course Evaluation", kind="course", semester="Fall 2026", status="open")
        question = SurveyQuestion(kind="course", label="Overall", text="Overall rating", position=1)
        self.db.add_all([student, teacher, course, survey, question])
        self.db.add_all(TopicCategory(**topic) for topic in DEFAULT_TOPICS)
        self.db.commit()
        invalidate_topics()
        self.student, self.course, self.survey, self.question = student, course, survey, question

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        invalidate_topics()

    def test_anonymous_submission_is_analyzed_before_commit(self):
        result = submit(
            self.survey.id,
            SubmitIn(
                course_id=self.course.id,
                ratings={self.question.id: 4},
                comment="The instructor was excellent, but the workload was terrible and deadlines were stressful.",
            ),
            user=self.student,
            db=self.db,
        )

        feedback = self.db.scalar(select(Feedback))
        receipt = self.db.scalar(select(SubmissionReceipt))
        self.assertTrue(result["ok"])
        self.assertIsNotNone(receipt)
        self.assertEqual(feedback.sentiment, "negative")
        self.assertIn("Teaching Quality", feedback.topics)
        self.assertIn("Workload", feedback.topics)
        self.assertEqual(feedback.aspects["Teaching Quality"], "positive")
        self.assertEqual(feedback.aspects["Workload"], "negative")
        self.assertGreater(feedback.confidence, 0)


if __name__ == "__main__":
    unittest.main()
