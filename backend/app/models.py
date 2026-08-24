import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Learner(Base):
    __tablename__ = "learners"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    experience_level: Mapped[str] = mapped_column(String, default="Student")
    interests: Mapped[list] = mapped_column(JSON, default=list)
    goal: Mapped[str] = mapped_column(Text, default="")
    learning_preference: Mapped[str] = mapped_column(String, default="hands-on")
    hours_per_week: Mapped[int] = mapped_column(Integer, default=10)
    hours_per_day: Mapped[int] = mapped_column(Integer, default=2)
    budget: Mapped[str] = mapped_column(String, default="free")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    target_role: Mapped[str] = mapped_column(String, default="")
    skill_gaps: Mapped[list] = mapped_column(JSON, default=list)
    duration_months: Mapped[int] = mapped_column(Integer, default=0)
    goal_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    goal_subskills: Mapped[list] = mapped_column(JSON, default=list)
    active_skill_id: Mapped[str] = mapped_column(String, default="")
    last_active_date: Mapped[str] = mapped_column(String, default="")
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    completed_courses: Mapped[list["CompletedCourse"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    paths: Mapped[list["LearningPath"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )


class CompletedCourse(Base):
    __tablename__ = "completed_courses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    skills: Mapped[list] = mapped_column(JSON, default=list)

    learner: Mapped[Learner] = relationship(back_populates="completed_courses")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    skill_id: Mapped[str] = mapped_column(String, default="", index=True)
    title: Mapped[str] = mapped_column(String, default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    learner: Mapped["Learner"] = relationship(back_populates="chat_sessions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    session_id: Mapped[str] = mapped_column(String, default="", index=True)
    skill_id: Mapped[str] = mapped_column(String, default="", index=True)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    learner: Mapped[Learner] = relationship(back_populates="chat_messages")


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    skill_id: Mapped[str] = mapped_column(String, default="", index=True)
    goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    learner: Mapped[Learner] = relationship(back_populates="paths")
    items: Mapped[list["PathItem"]] = relationship(
        back_populates="path", cascade="all, delete-orphan", order_by="PathItem.order"
    )


class PathItem(Base):
    __tablename__ = "path_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    path_id: Mapped[str] = mapped_column(ForeignKey("learning_paths.id"), index=True)
    catalog_id: Mapped[str] = mapped_column(String, index=True)
    order: Mapped[int] = mapped_column(Integer)
    item_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, default="")
    url: Mapped[str] = mapped_column(String, default="")
    skill_id: Mapped[str] = mapped_column(String, default="")
    skill_name: Mapped[str] = mapped_column(String, default="")
    topic_id: Mapped[str] = mapped_column(String, default="", index=True)
    resources: Mapped[list] = mapped_column(JSON, default=list)
    phase: Mapped[str] = mapped_column(String, default="")
    week: Mapped[int] = mapped_column(Integer, default=1)
    milestone_title: Mapped[str] = mapped_column(String, default="")
    prereq_ids: Mapped[list] = mapped_column(JSON, default=list)
    why: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="todo")
    feedback: Mapped[str] = mapped_column(String, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    path: Mapped[LearningPath] = relationship(back_populates="items")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    skill_id: Mapped[str] = mapped_column(String, default="", index=True)
    goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="in_progress")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    learner: Mapped[Learner] = relationship(back_populates="assessments")
    items: Mapped[list["AssessmentItem"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentItem.order"
    )


class AssessmentItem(Base):
    __tablename__ = "assessment_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    skill_id: Mapped[str] = mapped_column(String)
    skill_name: Mapped[str] = mapped_column(String, default="")
    topic_id: Mapped[str] = mapped_column(String, default="", index=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String, default="medium")
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    correct: Mapped[str] = mapped_column(String, default="")
    learner_answer: Mapped[str] = mapped_column(String, default="")
    is_correct: Mapped[int] = mapped_column(Integer, default=-1)

    assessment: Mapped[Assessment] = relationship(back_populates="items")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String, default="general")
    taxonomy_version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String, default="catalog")

    topics: Mapped[list["SkillTopic"]] = relationship(back_populates="skill", cascade="all, delete-orphan")


class SkillTopic(Base):
    __tablename__ = "skill_topics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), index=True)
    parent_id: Mapped[str] = mapped_column(String, default="")
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, default="")
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    required: Mapped[int] = mapped_column(Integer, default=70)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    skill: Mapped[Skill] = relationship(back_populates="topics")


class LearnerSkill(Base):
    __tablename__ = "learner_skills"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    skill_id: Mapped[str] = mapped_column(String, index=True)
    overall_proficiency: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="not_assessed")


class LearnerTopicMastery(Base):
    __tablename__ = "learner_topic_mastery"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    topic_id: Mapped[str] = mapped_column(String, index=True)
    proficiency: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="not_assessed")
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)


class AcademicProfile(Base):
    __tablename__ = "academic_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    learner_id: Mapped[str] = mapped_column(ForeignKey("learners.id"), index=True)
    institution: Mapped[str] = mapped_column(String, default="")
    branch: Mapped[str] = mapped_column(String, default="")
    semester: Mapped[str] = mapped_column(String, default="")


class AcademicSubject(Base):
    __tablename__ = "academic_subjects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    academic_profile_id: Mapped[str] = mapped_column(ForeignKey("academic_profiles.id"), index=True)
    subject: Mapped[str] = mapped_column(String, default="")
    topic_ids: Mapped[list] = mapped_column(JSON, default=list)
    resources: Mapped[list] = mapped_column(JSON, default=list)
