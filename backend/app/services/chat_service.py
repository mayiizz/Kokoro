from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.core.groq_client import get_groq_chat, get_groq_response
from app.models import ChatMessage, ChatSession
from app.schemas.learner import LearnerUpdate
from app.services import path_service
from app.services.learner_service import (
    apply_required_for_goal,
    get_learner_or_404,
    learner_to_dict,
    merge_skills,
    normalize_skill,
    update_learner,
)


def _history(
    db: Session,
    learner_id: str,
    limit: int = 20,
    skill_id: str | None = None,
    session_id: str | None = None,
) -> List[ChatMessage]:
    q = db.query(ChatMessage).filter(ChatMessage.learner_id == learner_id)
    if session_id:
        q = q.filter(ChatMessage.session_id == session_id)
    elif skill_id == "":
        q = q.filter((ChatMessage.skill_id == "") | (ChatMessage.skill_id.is_(None)))
    elif skill_id:
        q = q.filter(ChatMessage.skill_id == skill_id)
    return q.order_by(ChatMessage.created_at.asc()).all()[-limit:]


def serialize_messages(messages: List[ChatMessage]) -> List[dict]:
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "skill_id": getattr(m, "skill_id", "") or "",
            "session_id": getattr(m, "session_id", "") or "",
        }
        for m in messages
    ]


def _title_from_message(text: str) -> str:
    clean = " ".join((text or "").strip().split())
    return (clean[:72] if clean else "New chat") or "New chat"


def serialize_session(session: ChatSession, preview: str = "") -> dict:
    return {
        "id": session.id,
        "skill_id": session.skill_id or "",
        "title": session.title or "New chat",
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "preview": preview,
    }


def backfill_sessions(db: Session, learner_id: str) -> None:
    orphans = (
        db.query(ChatMessage)
        .filter(ChatMessage.learner_id == learner_id)
        .filter((ChatMessage.session_id == "") | (ChatMessage.session_id.is_(None)))
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    if not orphans:
        return
    grouped: dict[str, list[ChatMessage]] = {}
    for message in orphans:
        grouped.setdefault(message.skill_id or "", []).append(message)
    now = datetime.utcnow()
    learner = get_learner_or_404(db, learner_id)
    active = getattr(learner, "active_skill_id", "") or ""
    for sid, msgs in grouped.items():
        assigned = sid or active
        title = next((m.content for m in msgs if m.role == "user"), "Chat")
        session = ChatSession(
            learner_id=learner_id,
            skill_id=assigned,
            title=_title_from_message(title),
            created_at=msgs[0].created_at or now,
            updated_at=msgs[-1].created_at or now,
        )
        db.add(session)
        db.flush()
        for message in msgs:
            message.session_id = session.id
            if assigned and not (message.skill_id or ""):
                message.skill_id = assigned
    db.commit()


def list_sessions(db: Session, learner_id: str, skill_id: str | None = None) -> dict:
    get_learner_or_404(db, learner_id)
    backfill_sessions(db, learner_id)
    q = db.query(ChatSession).filter(ChatSession.learner_id == learner_id)
    if skill_id is not None:
        q = q.filter(ChatSession.skill_id == (skill_id or ""))
    rows = q.order_by(ChatSession.updated_at.desc()).all()
    sessions = []
    for session in rows:
        last = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        sessions.append(serialize_session(session, (last.content[:80] if last else "")))
    return {"sessions": sessions}


def create_session(db: Session, learner_id: str, skill_id: str = "") -> dict:
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    sid = skill_id or ""
    if sid:
        try:
            skill_registry.set_active_skill(db, learner, sid)
            db.refresh(learner)
        except Exception:
            pass
    session = ChatSession(learner_id=learner_id, skill_id=sid, title="New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return serialize_session(session)


def _session_for_chat(db: Session, learner_id: str, skill_id: str, session_id: str | None) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session and session.learner_id == learner_id:
            return session
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Chat not found")
    session = (
        db.query(ChatSession)
        .filter(ChatSession.learner_id == learner_id, ChatSession.skill_id == (skill_id or ""))
        .order_by(ChatSession.updated_at.desc())
        .first()
    )
    if session:
        return session
    session = ChatSession(learner_id=learner_id, skill_id=skill_id or "", title="New chat")
    db.add(session)
    db.flush()
    return session


def _intent_from_message(learner, message: str) -> dict:
    prompt = f"""
Extract learning-goal information from the learner message.

Profile: {learner_to_dict(learner)}
Message: {message}

JSON:
{{
  "intent": "clarify" | "update_profile" | "generate_path" | "assess" | "question",
  "needs_clarification": boolean,
  "clarify_question": string or null,
  "name": string or null,
  "goal": string or null,
  "target_role": string or null,
  "current_skills": [string],
  "weak_areas": [string],
  "interests": [string] or null,
  "hours_per_day": number or null,
  "hours_per_week": number or null,
  "duration_months": number or null,
  "budget": "free" | "any" | null,
  "learning_preference": "visual" | "hands-on" | "reading" | null
}}

Rules:
- clarify if the goal is vague (e.g. "I want a job") and ask one specific question.
- generate_path if they explicitly want a plan/roadmap/path generated.
- assess if they want a quiz or to test their level.
- update_profile if they share skills, time, budget, or a clear goal without asking to generate yet.
- question for why / what's next / explanations.
"""
    try:
        data = get_groq_response(prompt)
    except Exception:
        from app.services.goal_service import parse_schedule

        lowered = message.lower().strip()
        data = {}
        if len(lowered.split()) < 6 and not any(
            w in lowered for w in ("analyst", "engineer", "developer", "ml", "data", "learn", "guitar", "piano")
        ):
            data = {"intent": "clarify", "needs_clarification": True, "clarify_question": "What role or skill are you aiming for, and what do you already know?"}
        elif any(w in lowered for w in ("quiz", "assess", "test me")):
            data = {"intent": "assess"}
        elif any(w in lowered for w in ("generate", "roadmap", "create a path", "build my path")):
            data = {"intent": "generate_path", "goal": message.strip()}
        elif any(w in lowered for w in ("become", "want to", "i know", "hour", "learn ")):
            data = {"intent": "update_profile", "goal": message.strip()}
            if "python" in lowered:
                data["current_skills"] = ["Python"]
            if "statistic" in lowered or "math" in lowered:
                data["weak_areas"] = ["Statistics"]
            if "free" in lowered:
                data["budget"] = "free"
            sched = parse_schedule(message)
            if sched.get("hours_per_day"):
                data["hours_per_day"] = max(1, int(round(sched["hours_per_day"])))
            if sched.get("duration_months"):
                data["duration_months"] = sched["duration_months"]
        else:
            data = {"intent": "question"}
    intent = data.get("intent") or "question"
    if intent not in ("clarify", "update_profile", "generate_path", "assess", "question"):
        intent = "question"
    data["intent"] = intent
    if data.get("needs_clarification"):
        data["intent"] = "clarify"
    return data


def _seed_extracted_skills(learner, current_skills: list, weak_areas: list):
    incoming = []
    for name in current_skills or []:
        incoming.append(normalize_skill({"name": name, "proficiency": 60, "source": "chat"}))
    for name in weak_areas or []:
        incoming.append(normalize_skill({"name": name, "proficiency": 25, "source": "chat"}))
    learner.skills = merge_skills(learner.skills or [], [s for s in incoming if s])
    apply_required_for_goal(learner)


def _apply_intent_profile(db, learner, intent: dict):
    fields = {}
    for key in ("name", "goal", "target_role", "experience_level", "learning_preference", "budget"):
        if intent.get(key):
            fields[key] = intent[key]
    if intent.get("interests"):
        merged = list(learner.interests or [])
        for interest in intent["interests"]:
            if interest and interest not in merged:
                merged.append(interest)
        fields["interests"] = merged
    if intent.get("hours_per_week"):
        try:
            fields["hours_per_week"] = int(intent["hours_per_week"])
        except (TypeError, ValueError):
            pass
    if intent.get("hours_per_day"):
        try:
            fields["hours_per_day"] = int(intent["hours_per_day"])
            fields.setdefault("hours_per_week", int(intent["hours_per_day"]) * 7)
        except (TypeError, ValueError):
            pass
    if intent.get("duration_months"):
        try:
            fields["duration_months"] = int(intent["duration_months"])
        except (TypeError, ValueError):
            pass
    if fields:
        update_learner(db, learner, LearnerUpdate(**fields))
        db.refresh(learner)
    _seed_extracted_skills(learner, intent.get("current_skills") or [], intent.get("weak_areas") or [])
    try:
        from app.services.goal_service import parse_schedule
        from app.services.skill_registry import resolve_for_learner

        extra = ""
        if not fields.get("duration_months") or not fields.get("hours_per_day"):
            sched = parse_schedule(intent.get("goal") or "")
            if sched.get("duration_months") and not getattr(learner, "duration_months", 0):
                learner.duration_months = int(sched["duration_months"])
            if sched.get("hours_per_day") and not fields.get("hours_per_day"):
                learner.hours_per_day = max(1, int(round(sched["hours_per_day"])))
        blob = intent.get("goal") or learner.goal or learner.target_role
        if blob:
            resolve_for_learner(db, learner, blob)
    except Exception:
        pass
    db.commit()
    db.refresh(learner)
    return learner


def _answer_question(learner, path, message: str, history: List[ChatMessage], mastery_blob: str = "") -> str:
    path_summary = "No active path yet."
    if path and path.get("items"):
        lines = [f"- [{item['status']}] {item['title']}: {item['why']}" for item in path["items"][:12]]
        nxt = path.get("next_action")
        path_summary = "Active path:\n" + "\n".join(lines)
        if nxt:
            path_summary += f"\nNext: {nxt['title']} — {nxt['why']}"
    messages = [
        {
            "role": "system",
            "content": (
                "You are Kokoro. Explain skill gaps and why resources were ordered using the skill graph. "
                "Do not invent catalog items. Do not claim you updated proficiency; only the backend can do that."
            ),
        },
        {"role": "user", "content": f"Profile:\n{learner_to_dict(learner)}\n\nMastery:\n{mastery_blob or 'n/a'}\n\n{path_summary}"},
    ]
    for msg in history[-8:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})
    try:
        return get_groq_chat(messages)
    except Exception:
        if path and path.get("next_action"):
            nxt = path["next_action"]
            return f"Your next step is **{nxt['title']}**. {nxt['why']}"
        return "Share a target role (for example ML engineer) and what you already know. Then take a short assessment so the path matches your real level."


def chat(
    db: Session,
    learner_id: str,
    message: str,
    skill_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    backfill_sessions(db, learner_id)
    session: ChatSession | None = None
    if session_id:
        session = _session_for_chat(db, learner_id, "", session_id)
        sid = skill_id if skill_id is not None else (session.skill_id or "")
    elif skill_id is not None:
        sid = skill_id
    else:
        sid = skill_registry.active_skill_id(learner, db)
    if sid:
        try:
            skill_registry.set_active_skill(db, learner, sid)
            db.refresh(learner)
        except Exception:
            pass
    if session is None:
        session = _session_for_chat(db, learner_id, sid or "", None)
    if (not session.title or session.title == "New chat") and message.strip():
        session.title = _title_from_message(message)
    session.updated_at = datetime.utcnow()
    if sid and not session.skill_id:
        session.skill_id = sid
    thread_sid = sid or session.skill_id or ""
    db.add(
        ChatMessage(
            learner_id=learner_id,
            session_id=session.id,
            skill_id=thread_sid,
            role="user",
            content=message.strip(),
        )
    )
    db.commit()
    db.refresh(session)

    intent = _intent_from_message(learner, message)
    path = path_service.get_path(db, learner_id)
    reply = ""
    actions = []
    mastery_blob = ""
    if thread_sid:
        mastery = skill_registry.list_learner_skills(db, learner)
        topics = [skill_registry.serialize_topic(t, skill_registry.get_mastery(db, learner.id, t.id)) for t in skill_registry.topics_for_skill(db, thread_sid)]
        mastery_blob = str({"enrolled": mastery, "topics": [{"name": t["name"], "status": t["status"], "proficiency": t["proficiency"]} for t in topics[:12]]})

    if intent["intent"] == "clarify":
        reply = intent.get("clarify_question") or "What skill are you aiming for, and what do you already know?"
    else:
        old_goal = (learner.goal or "") + (learner.target_role or "")
        learner = _apply_intent_profile(db, learner, intent)
        if skill_id is None and not session_id:
            sid = skill_registry.active_skill_id(learner, db)
            thread_sid = sid or thread_sid
            if sid and not session.skill_id:
                session.skill_id = sid
        new_goal = (learner.goal or "") + (learner.target_role or "")
        if intent["intent"] == "generate_path":
            if old_goal and new_goal and old_goal != new_goal and path:
                path = path_service.adapt_path(db, learner_id)
                reply = (
                    f"Your goal changed to {learner.goal or learner.target_role}. "
                    "I kept your skill scores and rebuilt the remaining path."
                )
            else:
                path = path_service.generate_path(db, learner_id)
                top = (path or {}).get("items") or []
                reply = (
                    f"Personalized path toward {learner.goal or learner.target_role or 'your goal'} "
                    f"({len(top)} steps).\n"
                    + "\n".join(f"- {i['title']}: {i['why']}" for i in top[:3])
                )
            actions = ["path"]
        elif intent["intent"] == "assess":
            reply = "Take the adaptive skill assessment so we can estimate topic proficiency instead of guessing."
            actions = ["assessment"]
        elif intent["intent"] == "update_profile":
            reply = (
                f"Got it. Active skill: {sid or learner.goal or learner.target_role or 'not set yet'}. "
                "A short assessment will measure your current level; then I can build a path around real topic gaps."
            )
            actions = ["assessment", "path"]
        else:
            reply = _answer_question(
                learner,
                path,
                message,
                _history(db, learner_id, skill_id=thread_sid, session_id=session.id),
                mastery_blob,
            )

    db.add(
        ChatMessage(
            learner_id=learner_id,
            session_id=session.id,
            skill_id=thread_sid,
            role="assistant",
            content=reply,
        )
    )
    session.updated_at = datetime.utcnow()
    db.commit()
    return {
        "reply": reply,
        "intent": intent.get("intent"),
        "actions": actions,
        "learner": learner_to_dict(learner),
        "path": path,
        "session_id": session.id,
        "session": serialize_session(session),
        "messages": serialize_messages(_history(db, learner_id, limit=50, session_id=session.id)),
    }


def history(
    db: Session,
    learner_id: str,
    skill_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    backfill_sessions(db, learner_id)
    if session_id:
        session = db.get(ChatSession, session_id)
        sid = (session.skill_id if session else "") or ""
        return {
            "messages": serialize_messages(_history(db, learner_id, limit=50, session_id=session_id)),
            "skill_id": sid,
            "session_id": session_id,
        }
    sid = skill_id if skill_id is not None else skill_registry.active_skill_id(learner, db)
    return {
        "messages": serialize_messages(_history(db, learner_id, limit=50, skill_id=sid if sid is not None else None)),
        "skill_id": sid or "",
    }
