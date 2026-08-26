from app.core.groq_client import get_groq_response
from app.schemas.responses import ResumeGenerationResponse


async def generate_resume_content(request) -> ResumeGenerationResponse:
    try:   
        # safely handle lists
        skills = ", ".join(request.skills or [])
        tools = ", ".join(request.tools or [])
        projects = "; ".join(request.projects or [])
        achievements = "; ".join(request.achievements or [])
        certifications = "; ".join(request.certifications or [])

        prompt = f"""
    Generate an ATS-optimized resume for the role "{request.target_role}".

    STRICT RULES:
    - Do NOT invent information
    - If a field is empty → skip that section
    - Professional formatting
    - No markdown symbols
    - Clean resume layout

    PERSONAL INFO:
    Name: {request.name}
    Email: {request.email}
    Phone: {request.phone}
    LinkedIn: {request.linkedin}
    GitHub: {request.github}

    EDUCATION:
    {request.education}

    SKILLS:
    {skills}

    TOOLS:
    {tools}

    PROJECTS:
    {projects}

    ACHIEVEMENTS:
    {achievements}

    CERTIFICATIONS:
    {certifications}

    ACADEMIC DETAILS:
    {request.academic_details}

    TASK:
    1. Write professional summary
    2. List skills optimized for ATS
    3. Rewrite projects professionally
    4. Estimate ATS Match %
    5. List missing keywords

    Return STRICT JSON:

    {{
    "ats_optimized_resume_text": "resume text",
    "ats_match_percentage": 85,
    "missing_keywords": ["example"]
    }}
    """

        response_data = get_groq_response(prompt)

        # Ensure JSON parsing safety
        if isinstance(response_data, str):
            import json
            response_data = json.loads(response_data)

        return ResumeGenerationResponse(**response_data)
    except Exception as e:
        print("\n\n🔥🔥 BACKEND CRASH 🔥🔥")
        import traceback
        traceback.print_exc()
        raise e