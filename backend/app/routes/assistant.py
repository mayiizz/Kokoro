from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.learner import ChatRequest, ChatSessionCreate
from app.services import chat_service

router = APIRouter()


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    if not payload.message or not payload.message.strip():
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Message is required")
    return chat_service.chat(db, payload.learner_id, payload.message, payload.skill_id, payload.session_id)


@router.get("/history/{learner_id}")
def history(
    learner_id: str,
    skill_id: str | None = None,
    session_id: str | None = None,
    db: Session = Depends(get_db),
):
    return chat_service.history(db, learner_id, skill_id, session_id)


@router.get("/sessions/{learner_id}")
def sessions(learner_id: str, skill_id: str | None = None, db: Session = Depends(get_db)):
    return chat_service.list_sessions(db, learner_id, skill_id)


@router.post("/sessions")
def create_session(payload: ChatSessionCreate, db: Session = Depends(get_db)):
    return chat_service.create_session(db, payload.learner_id, payload.skill_id or "")
