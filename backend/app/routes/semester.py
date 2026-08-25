from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.semester_service import analyze_semester
from app.utils.syllabus_reader import read_syllabus
from app.schemas.responses import SemesterAnalysisResponse
from app.models import AcademicProfile, AcademicSubject
from app.services.learner_service import get_learner_or_404

router = APIRouter()

@router.post("/analyze", response_model=SemesterAnalysisResponse)
async def analyze_semester_endpoint(
    syllabus_text: Optional[str] = Form(None),
    syllabus_file: Optional[UploadFile] = File(None),
    manual_semester: Optional[str] = Form(None)
):
    try:
        text_content = await read_syllabus(file=syllabus_file, text=syllabus_text)

        if not text_content and not manual_semester:
            raise HTTPException(status_code=400, detail="Either syllabus text/file or manual semester is required")

        analysis = await analyze_semester(text_content, manual_semester)
        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roadmap/{learner_id}")
def academic_roadmap(learner_id: str, db: Session = Depends(get_db)):
    get_learner_or_404(db, learner_id)
    profile = db.query(AcademicProfile).filter(AcademicProfile.learner_id == learner_id).first()
    if not profile:
        return {"profile": None, "subjects": []}
    subjects = db.query(AcademicSubject).filter(AcademicSubject.academic_profile_id == profile.id).all()
    return {
        "profile": {"institution": profile.institution, "branch": profile.branch, "semester": profile.semester},
        "subjects": [
            {"subject": s.subject, "topic_ids": s.topic_ids or [], "resources": getattr(s, "resources", None) or []}
            for s in subjects
        ],
    }
