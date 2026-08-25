from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.schemas.responses import RoleFitRequest, RoleFitResponse
from app.services.role_fit_service import analyze_role_fit
from app.db import SessionLocal
from app.services.learner_service import get_learner_or_404
from app.services import skill_registry

router = APIRouter()

@router.post("/analyze", response_model=RoleFitResponse)
async def role_fit_endpoint(request: RoleFitRequest):
    try:
        fit_data = await analyze_role_fit(
            target_role=request.target_role,
            current_skills=request.current_skills or [],
            job_description=request.job_description or "",
            resume_text=request.resume_text or "",
        )
        return fit_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GapAnalysisRequest(BaseModel):
    learner_id: str
    target_role: str
    missing_skills: list[str] = []


@router.post("/gap-analysis")
def gap_analysis(payload: GapAnalysisRequest):
    db = SessionLocal()
    try:
        learner = get_learner_or_404(db, payload.learner_id)
        gaps = []
        for name in payload.missing_skills:
            try:
                resolved = skill_registry.resolve_for_learner(db, learner, name)
                sid = resolved["skill"]["id"]
                enrolled = next((s for s in skill_registry.list_learner_skills(db, learner) if s["id"] == sid), None)
                gaps.append(
                    {
                        "skill_id": sid,
                        "name": resolved["skill"]["name"],
                        "current": enrolled["overall_proficiency"] if enrolled else 0,
                        "required": 70,
                        "priority": "high",
                    }
                )
            except Exception:
                gaps.append({"skill_id": name.lower().replace(" ", "-"), "name": name, "current": 0, "required": 70, "priority": "high"})
        try:
            skill_registry.resolve_for_learner(db, learner, payload.target_role)
        except Exception:
            pass
        db.commit()
        return {"target_role": payload.target_role, "gaps": gaps, "active_skill_id": learner.active_skill_id or ""}
    finally:
        db.close()
