from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SkillEntry(BaseModel):
    name: str
    skill_id: Optional[str] = None
    source: str = "manual"
    level: str = "beginner"
    proficiency: Optional[int] = None
    required: Optional[int] = None
    evidence: List[str] = []


class CompletedCourseOut(BaseModel):
    id: str
    title: str
    skills: List[str] = []


class LearnerOut(BaseModel):
    id: str
    email: str
    name: str = ""
    experience_level: str = "Student"
    interests: List[str] = []
    goal: str = ""
    learning_preference: str = "hands-on"
    hours_per_week: int = 10
    hours_per_day: int = 2
    duration_months: int = 0
    budget: str = "free"
    skills: List[SkillEntry] = []
    target_role: str = ""
    skill_gaps: List[str] | List[dict] = []
    streak_days: int = 0
    last_active_date: str = ""
    completed_courses: List[CompletedCourseOut] = []


class LoginRequest(BaseModel):
    email: str
    name: Optional[str] = None


class LearnerUpdate(BaseModel):
    name: Optional[str] = None
    experience_level: Optional[str] = None
    interests: Optional[List[str]] = None
    goal: Optional[str] = None
    learning_preference: Optional[str] = None
    hours_per_week: Optional[int] = None
    hours_per_day: Optional[int] = None
    duration_months: Optional[int] = None
    budget: Optional[str] = None
    skills: Optional[List[SkillEntry]] = None
    target_role: Optional[str] = None
    skill_gaps: Optional[List[str] | List[dict]] = None


class CompletedCourseCreate(BaseModel):
    title: str
    skills: List[str] = []


class FromSemesterRequest(BaseModel):
    skills: List[str]
    semester: Optional[str] = None


class FromRoleFitRequest(BaseModel):
    target_role: str
    missing_skills: List[str] = []
    strengths: List[str] = []
    role_fit_percentage: Optional[int] = None


class ChatRequest(BaseModel):
    learner_id: str
    message: str
    skill_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatSessionCreate(BaseModel):
    learner_id: str
    skill_id: Optional[str] = None


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class PathItemPatch(BaseModel):
    status: Optional[str] = None
    feedback: Optional[str] = None


class PathGenerateRequest(BaseModel):
    learner_id: str


class PathAdaptRequest(BaseModel):
    learner_id: str
