from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import gap_service, skill_registry
from app.services.learner_service import get_learner_or_404

router = APIRouter()


class ResolveRequest(BaseModel):
    name: str
    learner_id: str | None = None


@router.get("")
@router.get("/")
def list_skills(db: Session = Depends(get_db)):
    skill_registry.seed_catalog_skills(db)
    from app.models import Skill

    skills = db.query(Skill).all()
    return {"skills": [skill_registry.serialize_skill(s) for s in skills]}


@router.post("/resolve")
def resolve(payload: ResolveRequest, db: Session = Depends(get_db)):
    if payload.learner_id:
        learner = get_learner_or_404(db, payload.learner_id)
        return skill_registry.resolve_for_learner(db, learner, payload.name)
    skill = skill_registry.resolve_skill(db, payload.name)
    db.commit()
    return {
        "skill": skill_registry.serialize_skill(skill),
        "topics": [skill_registry.serialize_topic(t) for t in skill_registry.topics_for_skill(db, skill.id)],
    }


@router.get("/gaps/{learner_id}")
def gaps(learner_id: str, db: Session = Depends(get_db)):
    return gap_service.gaps_for(db, learner_id)


@router.get("/{skill_id}/graph/{learner_id}")
def skill_topic_graph(skill_id: str, learner_id: str, db: Session = Depends(get_db)):
    learner = get_learner_or_404(db, learner_id)
    return skill_registry.topic_graph(db, learner, skill_id)


@router.get("/graph/{learner_id}")
def skill_graph(learner_id: str, db: Session = Depends(get_db)):
    learner = get_learner_or_404(db, learner_id)
    sid = skill_registry.active_skill_id(learner, db)
    if sid:
        return skill_registry.topic_graph(db, learner, sid)
    from app.services import goal_service, graph_service

    required = goal_service.learner_required_ids(learner)
    extra = goal_service.skill_defs_for_learner(learner)
    extra_prereqs = goal_service.extra_prereqs(learner)
    focus = (
        graph_service.ordered_skills(required, extra_prereqs=extra_prereqs)
        if (required or learner.goal or learner.target_role)
        else None
    )
    return graph_service.graph_payload(learner.skills or [], focus, extra_defs=extra)
