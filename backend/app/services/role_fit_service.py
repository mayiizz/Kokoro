from typing import List, Optional

from app.core.groq_client import get_groq_response
from app.schemas.responses import RoleFitResponse


async def analyze_role_fit(
    target_role: str,
    current_skills: List[str],
    job_description: str = "",
    resume_text: str = "",
) -> RoleFitResponse:

    skills_blob = ", ".join(current_skills) if current_skills else "(none listed)"
    prompt = f"""
You are a career guidance expert.

Target role: {target_role}
Job description (may be empty):
{job_description or "(role title only)"}

Resume text (may be empty):
{resume_text or "(not provided)"}

Known skills from the learner profile:
{skills_blob}

TASKS:
1. Calculate Role Fit Percentage (0–100) using BOTH the resume and listed skills vs the JD/role.
2. Mark demonstrated skills as strengths.
3. Identify missing skills required for the target role / JD.
4. Identify in-progress skills if they appear weakly in the resume.
5. Learning plan: 3–5 important topics per missing skill.
6. Recommend 3–5 example jobs/roles (not live listings) that fit this profile.

OUTPUT JSON only:
{{
  "role_fit_percentage": 0,
  "strengths": ["string"],
  "missing_skills": ["string"],
  "in_progress_skills": ["string"],
  "learning_plan": [{{"skill": "string", "topics": ["string"]}}],
  "recommended_jobs": [
    {{"title": "string", "seniority": "junior|mid|senior", "match_percent": 0, "why": "string", "missing_skills": ["string"]}}
  ]
}}
"""

    response_data = get_groq_response(prompt)
    response_data.setdefault("role_fit_percentage", 0)
    response_data.setdefault("strengths", [])
    response_data.setdefault("missing_skills", [])
    response_data.setdefault("in_progress_skills", [])
    response_data.setdefault("learning_plan", [])
    response_data.setdefault("recommended_jobs", [])
    if not isinstance(response_data["learning_plan"], list):
        response_data["learning_plan"] = []
    if not isinstance(response_data["recommended_jobs"], list):
        response_data["recommended_jobs"] = []
    return RoleFitResponse(**response_data)
