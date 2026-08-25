from app.core.groq_client import get_groq_response
from app.schemas.responses import RoadmapResponse

def _compute_constraints(months, hours_per_day):
    # defaults
    weeks = 12
    hours_per_week = 10

    if months:
        weeks = months * 4

    if hours_per_day:
        hours_per_week = min(int(hours_per_day * 7), 15)

    return weeks, hours_per_week


async def generate_career_roadmap(
    target_role: str,
    experience_level: str,
    months_available: int | None,
    hours_per_day: float | None
) -> RoadmapResponse:

    total_weeks, max_hours_per_week = _compute_constraints(
        months_available,
        hours_per_day
    )

    prompt = f"""
You are an expert career roadmap planner.

GOAL
----
Target role: {target_role}
Experience level: {experience_level}

TIME CONSTRAINTS (STRICT — MUST FOLLOW)
---------------------------------------
Total weeks available: {total_weeks}
Maximum hours per week: {max_hours_per_week}

CRITICAL RULES (DO NOT IGNORE)
------------------------------
1. You MUST generate EXACTLY {total_weeks} weeks.
2. Each week MUST have estimated_hours ≤ {max_hours_per_week}.
3. Weeks must be progressive and non-repetitive.
4. If constraints are tight, reduce depth — do NOT exceed hours.
5. If constraints are generous, increase depth and projects.
6. Changing time inputs MUST change the roadmap structure.

OUTPUT REQUIREMENTS
-------------------
- Week-by-week roadmap
- Practical, role-specific topics
- Clear practice tasks
- Realistic pacing

OUTPUT FORMAT (STRICT JSON ONLY)
--------------------------------
{{
  "feasible": boolean,
  "recommendation": "string",
  "roadmap": [
    {{
      "week": 1,
      "focus": "string",
      "topics": ["string"],
      "practice": "string",
      "estimated_hours": int
    }}
  ]
}}
"""

    response = get_groq_response(prompt)

    return RoadmapResponse(**response)
