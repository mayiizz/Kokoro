from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import assessment_service

router = APIRouter()


class GenerateRequest(BaseModel):
    learner_id: str
    skill_id: str | None = None


class SubmitRequest(BaseModel):
    assessment_id: str
    answers: list = []


class AnswerRequest(BaseModel):
    assessment_id: str
    item_id: str
    answer: str


@router.post("/generate")
def generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    return assessment_service.generate(db, payload.learner_id, payload.skill_id)


@router.get("/history/{learner_id}")
def history(learner_id: str, db: Session = Depends(get_db)):
    return assessment_service.history_for(db, learner_id)


@router.get("/{assessment_id}")
def get_one(assessment_id: str, db: Session = Depends(get_db)):
    return assessment_service.get_assessment(db, assessment_id)


@router.post("/answer")
def answer(payload: AnswerRequest, db: Session = Depends(get_db)):
    return assessment_service.answer(db, payload.assessment_id, payload.item_id, payload.answer)


@router.post("/submit")
def submit(payload: SubmitRequest, db: Session = Depends(get_db)):
    return assessment_service.submit(db, payload.assessment_id, payload.answers)
