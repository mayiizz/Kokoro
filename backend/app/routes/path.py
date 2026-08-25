from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from pydantic import BaseModel
from app.schemas.learner import PathAdaptRequest, PathGenerateRequest, PathItemPatch
from app.services import path_service

router = APIRouter()


@router.post("/generate")
def generate(payload: PathGenerateRequest, db: Session = Depends(get_db)):
    return path_service.generate_path(db, payload.learner_id)


class MoreResourcesRequest(BaseModel):
    learner_id: str
    topic_id: str


@router.post("/resources")
def more_resources(payload: MoreResourcesRequest, db: Session = Depends(get_db)):
    return path_service.more_resources_for_topic(db, payload.learner_id, payload.topic_id)


@router.get("/{learner_id}")
def get_path(learner_id: str, db: Session = Depends(get_db)):
    path = path_service.get_path(db, learner_id)
    if not path:
        return {"id": None, "learner_id": learner_id, "goal": "", "status": "empty", "items": [], "phases": [], "next_action": None}
    return path


@router.patch("/items/{item_id}")
def patch_item(item_id: str, payload: PathItemPatch, db: Session = Depends(get_db)):
    return path_service.patch_item(db, item_id, payload.status, payload.feedback)


@router.post("/adapt")
def adapt(payload: PathAdaptRequest, db: Session = Depends(get_db)):
    return path_service.adapt_path(db, payload.learner_id)
