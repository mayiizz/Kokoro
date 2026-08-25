from typing import Dict, List, Optional
import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.groq_client import get_groq_response
from app.models import Assessment, AssessmentItem, Skill
from app.services import path_service, skill_registry
from app.services.learner_service import (
    get_learner_or_404,
    touch_streak,
)

TARGET_QUESTIONS = 10
DIFF_UP = {"easy": "medium", "medium": "hard", "hard": "hard"}
DIFF_DOWN = {"hard": "medium", "medium": "easy", "easy": "easy"}
logger = logging.getLogger(__name__)


class QuestionIn(BaseModel):
    topic_id: str = ""
    skill_id: str = ""
    skill: str = ""
    skill_name: str = ""
    difficulty: str = "medium"
    question: str
    options: List[str] = Field(default_factory=list)
    correct: str = ""
    correct_answer: str = ""
    explanation: str = ""

    @field_validator("question")
    @classmethod
    def question_ok(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("question required")
        return v.strip()


def _public_item(item: AssessmentItem) -> dict:
    return {
        "id": item.id,
        "order": item.order,
        "skill_id": item.skill_id,
        "skill_name": getattr(item, "skill_name", "") or item.skill_id,
        "topic_id": getattr(item, "topic_id", "") or "",
        "difficulty": item.difficulty,
        "question": item.question,
        "options": item.options or [],
        "explanation": getattr(item, "explanation", "") or "",
    }


def _topics_as_dicts(db: Session, skill_id: str) -> List[dict]:
    return [
        {"id": t.id, "name": t.name, "prerequisites": t.prerequisites or [], "slug": t.slug}
        for t in skill_registry.leaf_topics_for_skill(db, skill_id)
    ]


def _match_topic(raw_id: str, topics: List[dict], fallback: dict) -> dict:
    from app.services.goal_service import slugify

    key = slugify(raw_id or "")
    for t in topics:
        if t["id"] == raw_id or t["id"] == key or t.get("slug") == key or t["id"].endswith(f"--{key}"):
            return t
    return fallback


def _parse_question(data: dict, topics: List[dict], fallback: dict) -> Optional[dict]:
    payload = data
    if isinstance(data.get("questions"), list) and data["questions"]:
        payload = data["questions"][0]
    if not isinstance(payload, dict):
        return None
    try:
        payload = QuestionIn.model_validate(payload).model_dump()
    except Exception:
        pass
    topic = _match_topic(str(payload.get("topic_id") or payload.get("skill_id") or ""), topics, fallback)
    name = (payload.get("skill") or payload.get("skill_name") or topic.get("name") or "").strip()
    options = [str(o) for o in (payload.get("options") or []) if str(o).strip()]
    correct = str(payload.get("correct") or payload.get("correct_answer") or "").strip()
    if correct.isdigit() and options:
        idx = int(correct)
        if 0 <= idx < len(options):
            correct = options[idx]
    question = str(payload.get("question") or "").strip()
    if len(options) < 2 or not correct or not question:
        return None
    if correct not in options:
        options = (options + [correct])[:4]
    difficulty = payload.get("difficulty") if str(payload.get("difficulty")) in ("easy", "medium", "hard") else "medium"
    if isinstance(payload.get("difficulty"), int):
        difficulty = {1: "easy", 2: "medium", 3: "hard"}.get(int(payload["difficulty"]), "medium")
    return {
        "skill_id": topic["id"],
        "skill_name": name or topic["name"],
        "topic_id": topic["id"],
        "difficulty": difficulty,
        "question": question,
        "options": options[:4],
        "correct": correct,
        "explanation": str(payload.get("explanation") or ""),
    }


def _llm_question(learner, topic: dict, difficulty: str, asked: List[str], skill_name: str) -> dict:
    prompt = f"""
One multiple-choice diagnostic question as JSON.

Skill: {skill_name}
Topic: {topic.get('name')} ({topic.get('id')})
Difficulty: {difficulty}
Avoid repeating: {asked[-4:] or "none"}

{{"topic_id":"{topic.get('id')}","skill":"{topic.get('name')}","difficulty":"{difficulty}","question":"...","options":["A","B","C","D"],"correct":"one option exactly","explanation":"one sentence"}}

About {topic.get('name')} for {skill_name} only — not unrelated domains. Exactly 4 options.
"""
    try:
        data = get_groq_response(prompt)
    except Exception as exc:
        logger.exception("Groq question generation failed")
        raise HTTPException(
            status_code=502,
            detail=f"Could not generate an assessment for this goal: {exc}",
        ) from exc
    parsed = _parse_question(data, [topic], topic)
    if not parsed:
        raise HTTPException(
            status_code=502,
            detail="The assessment model returned an invalid question. Please try again.",
        )
    parsed["difficulty"] = difficulty
    parsed["skill_id"] = topic.get("id")
    parsed["topic_id"] = topic.get("id")
    parsed["skill_name"] = topic.get("name") or parsed["skill_name"]
    return parsed


def _add_item(db: Session, assessment: Assessment, q: dict, order: int) -> AssessmentItem:
    item = AssessmentItem(
        assessment_id=assessment.id,
        order=order,
        skill_id=q["skill_id"],
        skill_name=q.get("skill_name") or q["skill_id"],
        topic_id=q.get("topic_id") or q["skill_id"],
        explanation=q.get("explanation") or "",
        difficulty=q.get("difficulty") or "medium",
        question=q["question"],
        options=q.get("options") or [],
        correct=q.get("correct") or "",
    )
    db.add(item)
    db.flush()
    return item


def serialize_assessment(assessment: Assessment, include_answers: bool = False) -> dict:
    items = []
    for item in sorted(assessment.items, key=lambda x: x.order):
        row = _public_item(item)
        if include_answers:
            row["correct"] = item.correct
            row["learner_answer"] = item.learner_answer
            row["is_correct"] = item.is_correct
        items.append(row)
    unanswered = [i for i in sorted(assessment.items, key=lambda x: x.order) if i.is_correct == -1]
    answered = sum(1 for i in assessment.items if i.is_correct != -1)
    current = _public_item(unanswered[0]) if unanswered else None
    return {
        "id": assessment.id,
        "learner_id": assessment.learner_id,
        "skill_id": getattr(assessment, "skill_id", "") or "",
        "goal": assessment.goal,
        "status": assessment.status,
        "items": items,
        "current_item": current,
        "answered": answered,
        "total": TARGET_QUESTIONS,
    }


def generate(db: Session, learner_id: str, skill_id: str | None = None) -> dict:
    learner = get_learner_or_404(db, learner_id)
    sid = (skill_id or "").strip() or skill_registry.active_skill_id(learner, db)
    if not sid:
        blob = (learner.goal or learner.target_role or "").strip()
        if not blob:
            raise HTTPException(status_code=400, detail="Select a skill or set a learning goal before starting an assessment.")
        skill_registry.resolve_for_learner(db, learner, blob)
        sid = skill_registry.active_skill_id(learner, db)
    if not sid:
        raise HTTPException(status_code=400, detail="Could not determine the skill for this assessment.")
    skill_registry.ensure_learner_skill(db, learner, sid)
    from app.models import Skill

    skill = db.get(Skill, sid)
    topics = _topics_as_dicts(db, sid)
    if not topics:
        raise HTTPException(status_code=400, detail="This skill has no topics to assess.")
    first = topics[0]
    q = _llm_question(learner, first, "easy", [], skill.name if skill else sid)
    assessment = Assessment(
        learner_id=learner.id,
        skill_id=sid,
        goal=learner.goal or (skill.name if skill else sid),
        status="in_progress",
    )
    db.add(assessment)
    db.flush()
    _add_item(db, assessment, q, 1)
    db.commit()
    db.refresh(assessment)
    return serialize_assessment(assessment, include_answers=False)


def get_assessment(db: Session, assessment_id: str) -> dict:
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return serialize_assessment(assessment, include_answers=assessment.status == "completed")


def _next_topic(db: Session, assessment: Assessment, last: AssessmentItem, correct: bool) -> dict:
    topics = _topics_as_dicts(db, assessment.skill_id or "")
    by_id = {t["id"]: t for t in topics}
    last_id = last.topic_id or last.skill_id
    if not correct:
        topic = by_id.get(last_id)
        if topic:
            for pid in topic.get("prerequisites") or []:
                if pid in by_id:
                    return by_id[pid]
            return topic
    asked = {i.topic_id or i.skill_id for i in assessment.items}
    for topic in topics:
        if topic["id"] not in asked:
            return topic
    return by_id.get(last_id) or topics[0]


def _continue_after_score(db: Session, assessment: Assessment, last: AssessmentItem) -> dict:
    learner = assessment.learner
    answered = sum(1 for i in assessment.items if i.is_correct != -1)
    unanswered = [i for i in sorted(assessment.items, key=lambda x: x.order) if i.is_correct == -1]
    if unanswered:
        payload = serialize_assessment(assessment)
        payload["next_item"] = _public_item(unanswered[0])
        payload["correct"] = bool(last.is_correct)
        payload["done"] = False
        return payload
    if answered >= TARGET_QUESTIONS or assessment.status in ("ready_to_submit", "completed"):
        assessment.status = "ready_to_submit"
        db.commit()
        result = submit(db, assessment.id, [])
        result["next_item"] = None
        result["correct"] = bool(last.is_correct)
        result["done"] = True
        return result
    difficulty = DIFF_UP.get(last.difficulty, "medium") if last.is_correct else DIFF_DOWN.get(last.difficulty, "easy")
    nxt = _next_topic(db, assessment, last, bool(last.is_correct))
    asked = [i.question for i in assessment.items]
    from app.models import Skill

    skill = db.get(Skill, assessment.skill_id) if assessment.skill_id else None
    q = _llm_question(learner, nxt, difficulty, asked, skill.name if skill else nxt.get("name", ""))
    next_item = _add_item(db, assessment, q, answered + 1)
    db.commit()
    db.refresh(assessment)
    payload = serialize_assessment(assessment)
    payload["next_item"] = _public_item(next_item)
    payload["correct"] = bool(last.is_correct)
    payload["done"] = False
    return payload


def answer(db: Session, assessment_id: str, item_id: str, given: str) -> dict:
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.status == "completed":
        serialized = serialize_assessment(assessment, include_answers=True)
        learner = assessment.learner
        return {
            **serialized,
            "assessment": serialized,
            "next_item": None,
            "done": True,
            "explanation": "This assessment is already completed.",
            "learner": __import__("app.services.learner_service", fromlist=["learner_to_dict"]).learner_to_dict(learner),
            "path": None,
        }
    item = next((i for i in assessment.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Question not found")
    if item.is_correct == -1:
        item.learner_answer = (given or "").strip()
        item.is_correct = 1 if item.learner_answer == item.correct else 0
        db.commit()
    return _continue_after_score(db, assessment, item)


def submit(db: Session, assessment_id: str, answers: List[dict]) -> dict:
    assessment = db.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    learner = assessment.learner
    by_id = {i.id: i for i in assessment.items}
    for ans in answers:
        item = by_id.get(ans.get("item_id") or ans.get("id"))
        if not item or item.is_correct != -1:
            continue
        given = str(ans.get("answer") or "").strip()
        item.learner_answer = given
        item.is_correct = 1 if given == item.correct else 0

    per_topic: Dict[str, List[int]] = {}
    for item in assessment.items:
        if item.is_correct == -1:
            continue
        tid = item.topic_id or item.skill_id
        per_topic.setdefault(tid, []).append(100 if item.is_correct else 20)

    skipped, inserted_focus = [], []
    for tid, scores in per_topic.items():
        quiz = int(sum(scores) / len(scores))
        skill_registry.apply_topic_score(db, learner, tid, quiz)
        row = skill_registry.get_mastery(db, learner.id, tid)
        from app.models import SkillTopic

        topic = db.get(SkillTopic, tid)
        required = int(topic.required) if topic else 70
        if row and row.proficiency >= required - 5:
            skipped.append(tid)
        elif row and row.proficiency < required * 0.5:
            inserted_focus.append(tid)
    if assessment.skill_id:
        skill_registry.rollup_skill(db, learner, assessment.skill_id)

    assessment.status = "completed"
    touch_streak(learner)
    db.commit()

    path = None
    try:
        path = path_service.replan_from_assessment(db, learner.id, skip_skills=skipped, focus_skills=inserted_focus)
    except Exception:
        logger.exception("Path rebuild after assessment failed; scores were still saved")

    explanation = _explain(db, learner, skipped, inserted_focus)
    if not path:
        explanation = (explanation + " Open Learning Path and generate it if it is empty — Groq was rate-limited just now.").strip()

    return {
        "assessment": serialize_assessment(assessment, include_answers=True),
        "skill_scores": {tid: int(sum(v) / len(v)) for tid, v in per_topic.items()},
        "skipped_skills": skipped,
        "focus_skills": inserted_focus,
        "learner": __import__("app.services.learner_service", fromlist=["learner_to_dict"]).learner_to_dict(learner),
        "path": path,
        "explanation": explanation,
        "done": True,
    }


def _explain(db: Session, learner, skipped: List[str], focus: List[str]) -> str:
    from app.models import SkillTopic

    def names(ids):
        out = []
        for sid in ids:
            topic = db.get(SkillTopic, sid)
            out.append(topic.name if topic else sid)
        return out

    bits = []
    if skipped:
        bits.append(
            f"You demonstrated sufficient proficiency in {', '.join(names(skipped))}; introductory items for those topics can be skipped."
        )
    if focus:
        bits.append(f"Lower scores on {', '.join(names(focus))} mean we added prerequisite practice before advancing.")
    return " ".join(bits) or "Your skill profile was updated from this assessment."


def history_for(db: Session, learner_id: str) -> dict:
    get_learner_or_404(db, learner_id)
    rows = (
        db.query(Assessment)
        .filter(Assessment.learner_id == learner_id)
        .order_by(Assessment.created_at.desc())
        .limit(20)
        .all()
    )
    out = []
    for a in rows:
        skill = db.get(Skill, a.skill_id) if getattr(a, "skill_id", "") else None
        matched = None if skill else skill_registry._match_existing(db, a.goal or "")
        skill_name = skill.name if skill else (matched.name if matched else "Assessment")
        out.append(
            {
                "id": a.id,
                "skill_id": getattr(a, "skill_id", "") or (matched.id if matched else ""),
                "skill_name": skill_name,
                "goal": a.goal,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "answered": sum(1 for i in a.items if i.is_correct != -1),
                "total": len(a.items),
            }
        )
    return {"assessments": out}
