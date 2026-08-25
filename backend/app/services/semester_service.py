from app.core.groq_client import get_groq_response
from app.schemas.responses import SemesterAnalysisResponse

async def analyze_semester(
    syllabus_text: str,
    manual_semester: str = None
) -> SemesterAnalysisResponse:

    prompt = f"""
You are an academic-to-industry mapping expert.

Analyze the following academic syllabus and extract structured, industry-oriented insights.

Syllabus Content:
{syllabus_text}

Manual Semester Override:
{manual_semester if manual_semester else "Auto-detect"}

TASKS:
1. Detect the semester (e.g., "Semester 5").
2. Identify Theory subjects and their topics.
3. Identify Lab/Practical subjects and their topics.
4. For EACH topic:
   - Assess industry relevance (High/Medium/Low)
   - Map it to ONE clear industry skill
   - List commonly used industry tools/frameworks
   - Suggest additional topics/skills that improve industry readiness
5. Extract a consolidated list of industry skills:
   - Categorize each as Core / Tools / Concepts
   - Mark status as Learned / Learning
6. Estimate an overall industry relevance for the semester.
7. Calculate a semester readiness score (0–100).
8. Create a summary card with key stats (subjects count, skills count, top skills).

OUTPUT RULES:
- Return ONLY valid JSON
- Do NOT include explanations or text outside JSON
- Keep suggestions realistic for undergraduate students

OUTPUT JSON STRUCTURE (STRICT):

{{
  "semester_detected": "string",

  "theory_subjects": [
    {{
      "name": "string",
      "topics": [
        {{
          "name": "string",
          "industry_relevance": "High/Medium/Low",
          "industry_skill": "string",
          "industry_tools": ["string"],
          "extra_learning": ["string"]
        }}
      ]
    }}
  ],

  "lab_subjects": [
    {{
      "name": "string",
      "topics": [
        {{
          "name": "string",
          "industry_relevance": "High/Medium/Low",
          "industry_skill": "string",
          "industry_tools": ["string"],
          "extra_learning": ["string"]
        }}
      ]
    }}
  ],

  "industry_skills": [
    {{
      "name": "string",
      "category": "Core/Tools/Concepts",
      "status": "Learned/Learning"
    }}
  ],

  "industry_relevance": "High/Medium/Low",
  "semester_readiness_score": 0,
  "summary_card_data": {{
    "total_subjects": 0,
    "total_topics": 0,
    "total_skills": 0,
    "top_industry_skills": ["string"]
  }}
}}
"""

    response_data = get_groq_response(prompt)
    return SemesterAnalysisResponse(**response_data)
