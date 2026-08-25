from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.roadmap_service import generate_career_roadmap
from app.schemas.responses import RoadmapResponse

router = APIRouter()

class RoadmapRequest(BaseModel):
    target_role: str
    experience_level: str
    months_available: int | None = None
    hours_per_day: float | None = None

@router.post("/generate", response_model=RoadmapResponse)
async def roadmap_endpoint(request: RoadmapRequest):
    try:
        # ✅ THIS WAS THE BUG — AWAIT IS REQUIRED
        roadmap = await generate_career_roadmap(
            target_role=request.target_role,
            experience_level=request.experience_level,
            months_available=request.months_available,
            hours_per_day=request.hours_per_day
        )
        return roadmap
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
