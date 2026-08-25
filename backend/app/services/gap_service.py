from typing import List, Optional

from sqlalchemy.orm import Session

from app.services import goal_service, graph_service, skill_registry
from app.services.learner_service import apply_required_for_goal, get_learner_or_404, merge_skills


def skill_map(learner) -> dict:
    merged = merge_skills(learner.skills or [], [])
    return {s["skill_id"]: s for s in merged}


def compute_gaps(learner, db: Optional[Session] = None) -> List[dict]:
    if db is not None:
        sid = skill_registry.active_skill_id(learner, db)
        if sid:
            skill_registry.ensure_learner_skill(db, learner, sid)
            topics = skill_registry.weak_topics(db, learner, sid)
            all_topics = skill_registry.topics_for_skill(db, sid)
            by_id = {t.id: t for t in all_topics}
            extra = {t.id: list(t.prerequisites or []) for t in all_topics}
            ordered = graph_service.ordered_skills([t.id for t in all_topics], extra_prereqs=extra)
            weak_ids = {t.id for t in topics}
            rows = []
            for tid in ordered:
                topic = by_id.get(tid)
                if not topic:
                    continue
                m = skill_registry.get_mastery(db, learner.id, tid)
                current = int(m.proficiency) if m else 0
                required = int(topic.required or 70)
                gap = max(0, required - current)
                blocked = 0
                for p in topic.prerequisites or []:
                    pm = skill_registry.get_mastery(db, learner.id, p)
                    pcur = int(pm.proficiency) if pm else 0
                    preq = int((by_id.get(p).required if by_id.get(p) else 70) or 70)
                    if pcur < preq - 5:
                        blocked += 1
                status = m.status if m else "not_assessed"
                rows.append(
                    {
                        "skill_id": tid,
                        "topic_id": tid,
                        "name": topic.name,
                        "current": current,
                        "required": required,
                        "gap": gap,
                        "status": status,
                        "confidence": int(m.confidence) if m else 0,
                        "importance": 0.7,
                        "priority": round(gap * 0.7 * (1 + 0.25 * blocked), 2),
                        "prerequisites": topic.prerequisites or [],
                        "blocked_by": blocked,
                    }
                )
            if weak_ids:
                rows.sort(key=lambda r: (0 if r["skill_id"] in weak_ids else 1, -r["priority"], -r["gap"]))
            else:
                rows.sort(key=lambda r: (-r["priority"], -r["gap"]))
            return rows
    apply_required_for_goal(learner)
    extra = goal_service.skill_defs_for_learner(learner)
    extra_prereqs = goal_service.extra_prereqs(learner)
    required_ids = goal_service.learner_required_ids(learner)
    ordered = graph_service.ordered_skills(required_ids, extra_prereqs=extra_prereqs)
    by_id = skill_map(learner)
    index = {**graph_service.skill_index(), **extra}
    rows = []
    for sid in ordered:
        meta = index.get(sid)
        if not meta:
            continue
        current = int((by_id.get(sid) or {}).get("proficiency") or 0)
        required = int((by_id.get(sid) or {}).get("required") or meta.get("required") or 70)
        gap = max(0, required - current)
        blocked = 0
        for p in meta.get("prerequisites") or []:
            pcur = int((by_id.get(p) or {}).get("proficiency") or 0)
            preq = int((index.get(p) or {}).get("required") or 70)
            if pcur < preq - 5:
                blocked += 1
        importance = float(meta.get("importance") or 0.7)
        rows.append(
            {
                "skill_id": sid,
                "name": meta.get("name", sid),
                "current": current,
                "required": required,
                "gap": gap,
                "importance": importance,
                "priority": round(gap * importance * (1 + 0.25 * blocked), 2),
                "prerequisites": meta.get("prerequisites") or [],
                "blocked_by": blocked,
            }
        )
    rows.sort(key=lambda r: (-r["priority"], -r["gap"]))
    return rows


def gaps_for(db: Session, learner_id: str) -> dict:
    learner = get_learner_or_404(db, learner_id)
    rows = compute_gaps(learner, db)
    db.commit()
    return {
        "goal": learner.goal or "",
        "target_role": learner.target_role or "",
        "active_skill_id": getattr(learner, "active_skill_id", "") or "",
        "gaps": rows,
        "open_gaps": [r for r in rows if r["gap"] > 0],
    }
