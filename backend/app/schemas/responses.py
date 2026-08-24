from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# --- Shared Schemas ---

class Skill(BaseModel):
    name: str
    category: str  # Core / Tools / Concepts
    status: str    # Learned / Learning / To Learn

# --- Semester Analysis ---

class SemesterAnalysisRequest(BaseModel):
    syllabus_text: Optional[str] = None
    manual_semester: Optional[str] = None

class TopicResponse(BaseModel):
    name: str
    industry_relevance: str
    industry_skill: str
    industry_tools: List[str]
    extra_learning: List[str]

class SubjectResponse(BaseModel):
    name: str
    topics: List[TopicResponse]

class SummaryCardData(BaseModel):
    total_subjects: int
    total_topics: int
    total_skills: int
    top_industry_skills: List[str]

class SemesterAnalysisResponse(BaseModel):
    semester_detected: str
    theory_subjects: List[SubjectResponse]
    lab_subjects: List[SubjectResponse]
    industry_skills: List[Skill]
    industry_relevance: str
    semester_readiness_score: int
    summary_card_data: SummaryCardData

# --- Resume Generation ---

class ResumeGenerationRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

    education: Optional[str] = None
    summary: Optional[str] = None
    academic_details: Optional[str] = None

    skills: Optional[List[str]] = []
    tools: Optional[List[str]] = []
    projects: Optional[List[str]] = []
    achievements: Optional[List[str]] = []
    certifications: Optional[List[str]] = []

    target_role: str

class ResumeGenerationResponse(BaseModel):
    ats_optimized_resume_text: str
    ats_match_percentage: int
    missing_keywords: List[str]

# --- Role Fit Analysis ---

class RoleFitRequest(BaseModel):
    target_role: str
    current_skills: List[str] = []
    job_description: str = ""
    resume_text: str = ""

class LearningPlanItem(BaseModel):
    skill: str
    topics: List[str]

class RecommendedJob(BaseModel):
    title: str
    seniority: str = "mid"
    match_percent: int = 0
    why: str = ""
    missing_skills: List[str] = []

class RoleFitResponse(BaseModel):
    role_fit_percentage: int
    strengths: List[str]
    missing_skills: List[str]
    in_progress_skills: List[str]
    learning_plan: List[LearningPlanItem]
    recommended_jobs: List[RecommendedJob] = []

# --- Career Roadmap ---
class WeeklyRoadmap(BaseModel):
    week: int
    focus: str
    topics: List[str]
    practice: str
    estimated_hours: int

class RoadmapResponse(BaseModel):
    feasible: bool
    recommendation: str
    roadmap: List[WeeklyRoadmap]
