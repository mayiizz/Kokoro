from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.learner import (
    CompletedCourseCreate,
    FromRoleFitRequest,
    FromSemesterRequest,
    LearnerUpdate,
    LoginRequest,
)
from app.services import learner_service as svc
from app.services import skill_registry

router = APIRouter()


class ActiveSkillRequest(BaseModel):
    skill_id: str


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    learner = svc.login_or_create(db, payload)
    return svc.learner_to_dict(learner)


@router.get("/{learner_id}")
def get_learner(learner_id: str, db: Session = Depends(get_db)):
    learner = svc.get_learner_or_404(db, learner_id)
    return svc.learner_to_dict(learner)


@router.get("/{learner_id}/skills")
def list_enrolled_skills(learner_id: str, db: Session = Depends(get_db)):
    learner = svc.get_learner_or_404(db, learner_id)
    return {"skills": skill_registry.list_learner_skills(db, learner), "active_skill_id": learner.active_skill_id or ""}


@router.put("/{learner_id}/active-skill")
def set_active_skill(learner_id: str, payload: ActiveSkillRequest, db: Session = Depends(get_db)):
    learner = svc.get_learner_or_404(db, learner_id)
    return skill_registry.set_active_skill(db, learner, payload.skill_id)


@router.put("/{learner_id}")
def update_learner(learner_id: str, payload: LearnerUpdate, db: Session = Depends(get_db)):
    learner = svc.get_learner_or_404(db, learner_id)
    learner = svc.update_learner(db, learner, payload)
    return svc.learner_to_dict(learner)


@router.post("/{learner_id}/courses")
def add_course(learner_id: str, payload: CompletedCourseCreate, db: Session = Depends(get_db)):
    learner = svc.get_learner_or_404(db, learner_id)
    learner = svc.add_completed_course(db, learner, payload)
    return svc.learner_to_dict(learner)


@router.post("/{learner_id}/from-semester")
def from_semester(learner_id: str, payload: FromSemesterRequest, db: Session = Depends(get_db)):
    learner = svc.get_learner_or_404(db, learner_id)
    learner = svc.apply_semester(db, learner, payload)
    return svc.learner_to_dict(learner)


@router.post("/{learner_id}/from-role-fit")
def from_role_fit(learner_id: str, payload: FromRoleFitRequest, db: Session = Depends(get_db)):
    learner = svc.get_learner_or_404(db, learner_id)
    learner = svc.apply_role_fit(db, learner, payload)
    return svc.learner_to_dict(learner)
