from datetime import datetime, date

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

ROLES = ("student", "faculty", "manager", "admin")
KINDS = ("course", "service", "survey")  # course evaluation / service review / general survey
SENTIMENTS = ("positive", "neutral", "negative")
ACTION_STATUSES = ("planned", "in_progress", "done")


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(160))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    student_id: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(16), index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # False = banned
    ban_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    banned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Embedded in every JWT; bumping it (e.g. on password change) invalidates all issued tokens.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    department: Mapped[Department | None] = relationship()


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    instructor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    department: Mapped[Department] = relationship()
    instructor: Mapped[User | None] = relationship()


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    category: Mapped[str] = mapped_column(String(80), default="General")


class TopicCategory(Base):
    __tablename__ = "topic_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="#8b5cff")
    keywords: Mapped[list] = mapped_column(JSON, default=list)  # word stems in en / ru / kk
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Survey(Base):
    __tablename__ = "surveys"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(16))
    semester: Mapped[str] = mapped_column(String(24), index=True)
    status: Mapped[str] = mapped_column(String(16), default="open")  # draft | open | closed
    question: Mapped[str] = mapped_column(Text, default="What did you like, and what should be improved?")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int | None] = mapped_column(ForeignKey("surveys.id", ondelete="SET NULL"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    semester: Mapped[str] = mapped_column(String(24), index=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Only the anonymized text is stored; the raw submission never reaches the database.
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(4), default="en")
    sentiment: Mapped[str] = mapped_column(String(16), index=True, default="neutral")
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    aspects: Mapped[dict] = mapped_column(JSON, default=dict)  # {topic: "positive"|"neutral"|"negative"}
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    pii_masked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="form")  # form | import | seed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    course: Mapped[Course | None] = relationship()
    service: Mapped[Service | None] = relationship()
    department: Mapped[Department | None] = relationship()


class SubmissionReceipt(Base):
    """Records THAT a student answered a survey target (to block duplicates) without linking to the answer."""
    __tablename__ = "submission_receipts"
    __table_args__ = (UniqueConstraint("user_id", "survey_id", "target_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"))
    target_key: Mapped[str] = mapped_column(String(40))
    # Rounded to the day so the receipt cannot be joined to a feedback row by timestamp
    submitted_on: Mapped[date] = mapped_column(Date, default=date.today)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(16))  # course | service | department
    scope_id: Mapped[int] = mapped_column(Integer)
    scope_name: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semester: Mapped[str] = mapped_column(String(24))
    previous_semester: Mapped[str] = mapped_column(String(24))
    negative_share: Mapped[float] = mapped_column(Float)
    previous_share: Mapped[float] = mapped_column(Float)
    top_topic: Mapped[str | None] = mapped_column(String(80), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # medium | high
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Action(Base):
    __tablename__ = "actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    topic: Mapped[str | None] = mapped_column(String(80), nullable=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    owner: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(16), default="planned")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    course: Mapped[Course | None] = relationship()
    service: Mapped[Service | None] = relationship()
