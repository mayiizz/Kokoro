from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import path_service

router = APIRouter()


@router.get("/{learner_id}")
def dashboard(learner_id: str, db: Session = Depends(get_db)):
    return path_service.dashboard_for(db, learner_id)
