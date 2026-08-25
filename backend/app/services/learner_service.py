from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import CompletedCourse, Learner
from app.schemas.learner import (
    CompletedCourseCreate,
    FromRoleFitRequest,
    FromSemesterRequest,
    LearnerUpdate,
    LoginRequest,
)
from app.services import graph_service

LEVEL_TO_PROF = {"beginner": 40, "intermediate": 65, "advanced": 85}


def normalize_skill(raw: dict, source: str = "manual") -> dict | None:
    name = (raw.get("name") or "").strip()
    skill_id = raw.get("skill_id") or graph_service.resolve_id(name)
    if not name and skill_id:
        meta = graph_service.skill_index().get(skill_id)
        name = meta["name"] if meta else skill_id
    if not name:
        return None
    if not skill_id:
        skill_id = name.lower().replace(" ", "-")
    meta = graph_service.skill_index().get(skill_id) or {}
    proficiency = raw.get("proficiency")
    if proficiency is None:
        proficiency = LEVEL_TO_PROF.get((raw.get("level") or "beginner").lower(), 40)
    return {
        "name": name,
        "skill_id": skill_id,
        "proficiency": int(max(0, min(100, proficiency))),
        "required": int(raw.get("required") or meta.get("required") or 70),
        "source": raw.get("source") or source,
        "level": raw.get("level") or "beginner",
        "evidence": list(raw.get("evidence") or []),
    }


def merge_skills(existing: list, incoming: list, replace: bool = False) -> list:
    by_key = {}
    if not replace:
        for skill in existing or []:
            normalized = normalize_skill(skill) if isinstance(skill, dict) else None
            if not normalized:
                continue
            by_key[normalized["skill_id"]] = normalized
    for skill in incoming or []:
        if not isinstance(skill, dict):
            continue
        normalized = normalize_skill(skill)
        if not normalized:
            continue
        key = normalized["skill_id"]
        if key in by_key and not replace:
            prev = by_key[key]
            prev["proficiency"] = max(prev["proficiency"], normalized["proficiency"])
            prev["required"] = max(prev["required"], normalized["required"])
            prev["source"] = normalized["source"] or prev["source"]
            evidence = list(prev.get("evidence") or [])
            for ev in normalized.get("evidence") or []:
                if ev not in evidence:
                    evidence.append(ev)
            prev["evidence"] = evidence[-8:]
        else:
            by_key[key] = normalized
    return list(by_key.values())


def apply_required_for_goal(learner: Learner) -> list:
    from app.services.goal_service import learner_required_ids, skill_defs_for_learner

    extra = skill_defs_for_learner(learner)
    required_ids = learner_required_ids(learner)
    if not required_ids:
        return learner.skills or []
    ordered = graph_service.ordered_skills(required_ids, extra_prereqs={sid: list(m.get("prerequisites") or []) for sid, m in extra.items()})
    incoming = []
    existing = {(s.get("skill_id") if isinstance(s, dict) else None) for s in (learner.skills or [])}
    index = graph_service.skill_index()
    for sid in ordered:
        meta = extra.get(sid) or index.get(sid)
        if not meta:
            continue
        if sid in existing:
            continue
        incoming.append(
            {
                "name": meta.get("name", sid),
                "skill_id": sid,
                "proficiency": 0,
                "required": meta.get("required", 70),
                "source": "goal",
            }
        )
    merged = merge_skills(learner.skills or [], incoming)
    by_id = {s["skill_id"]: s for s in merged}
    for sid in ordered:
        meta = extra.get(sid) or index.get(sid) or {}
        if sid in by_id:
            by_id[sid]["required"] = int(meta.get("required") or by_id[sid].get("required") or 70)
            if meta.get("name") and not by_id[sid].get("name"):
                by_id[sid]["name"] = meta["name"]
    learner.skills = list(by_id.values())
    return learner.skills


def bump_proficiency(learner: Learner, skill_id: str, delta: int, evidence: str, cap: int = 90) -> None:
    skills = merge_skills(learner.skills or [], [])
    found = False
    for skill in skills:
        if skill["skill_id"] == skill_id:
            skill["proficiency"] = int(max(0, min(cap, skill["proficiency"] + delta)))
            ev = list(skill.get("evidence") or [])
            ev.append(evidence)
            skill["evidence"] = ev[-8:]
            found = True
    if not found:
        meta = graph_service.skill_index().get(skill_id) or {"name": skill_id, "required": 70}
        skills.append(
            {
                "name": meta.get("name", skill_id),
                "skill_id": skill_id,
                "proficiency": max(0, min(cap, delta)),
                "required": meta.get("required", 70),
                "source": "path",
                "evidence": [evidence],
            }
        )
    learner.skills = skills


def blend_proficiency(old: int, quiz: int) -> int:
    return int(round(0.6 * old + 0.4 * quiz))


def touch_streak(learner: Learner) -> None:
    today = date.today().isoformat()
    last = learner.last_active_date or ""
    if last == today:
        return
    yesterday = date.fromordinal(date.today().toordinal() - 1).isoformat()
    if last == yesterday:
        learner.streak_days = (learner.streak_days or 0) + 1
    else:
        learner.streak_days = 1
    learner.last_active_date = today


def learner_to_dict(learner: Learner) -> dict:
    skills = merge_skills(learner.skills or [], [])
    return {
        "id": learner.id,
        "email": learner.email,
        "name": learner.name or "",
        "experience_level": learner.experience_level or "Student",
        "interests": learner.interests or [],
        "goal": learner.goal or "",
        "learning_preference": learner.learning_preference or "hands-on",
        "hours_per_week": learner.hours_per_week or 10,
        "hours_per_day": getattr(learner, "hours_per_day", None) or 2,
        "budget": getattr(learner, "budget", None) or "free",
        "skills": skills,
        "target_role": learner.target_role or "",
        "skill_gaps": learner.skill_gaps or [],
        "duration_months": getattr(learner, "duration_months", None) or 0,
        "active_skill_id": getattr(learner, "active_skill_id", None) or "",
        "streak_days": getattr(learner, "streak_days", None) or 0,
        "last_active_date": getattr(learner, "last_active_date", None) or "",
        "completed_courses": [
            {"id": c.id, "title": c.title, "skills": c.skills or []}
            for c in (learner.completed_courses or [])
        ],
    }


def get_learner_or_404(db: Session, learner_id: str) -> Learner:
    learner = db.get(Learner, learner_id)
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")
    return learner


def login_or_create(db: Session, payload: LoginRequest) -> Learner:
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email is required")
    learner = db.query(Learner).filter(Learner.email == email).first()
    if learner:
        if payload.name and not learner.name:
            learner.name = payload.name.strip()
            db.commit()
            db.refresh(learner)
        touch_streak(learner)
        db.commit()
        db.refresh(learner)
        return learner
    name = (payload.name or email.split("@")[0]).strip()
    learner = Learner(
        email=email,
        name=name,
        interests=[],
        skills=[],
        skill_gaps=[],
        budget="free",
        hours_per_day=2,
        streak_days=1,
        last_active_date=date.today().isoformat(),
    )
    db.add(learner)
    db.commit()
    db.refresh(learner)
    return learner


def update_learner(db: Session, learner: Learner, payload: LearnerUpdate) -> Learner:
    data = payload.model_dump(exclude_unset=True)
    if "skills" in data and data["skills"] is not None:
        data["skills"] = [s if isinstance(s, dict) else s.model_dump() for s in data["skills"]]
        data["skills"] = merge_skills([], data["skills"], replace=True)
    goal_changed = "goal" in data or "target_role" in data
    for key, value in data.items():
        setattr(learner, key, value)
    if goal_changed:
        blob = (learner.goal or learner.target_role or "").strip()
        if blob:
            try:
                from app.services.skill_registry import resolve_for_learner

                resolve_for_learner(db, learner, blob)
            except HTTPException:
                try:
                    from app.services.goal_service import ensure_decomposed

                    ensure_decomposed(learner)
                except HTTPException:
                    apply_required_for_goal(learner)
        else:
            apply_required_for_goal(learner)
    touch_streak(learner)
    db.commit()
    db.refresh(learner)
    return learner


def add_completed_course(db: Session, learner: Learner, payload: CompletedCourseCreate) -> Learner:
    course = CompletedCourse(
        learner_id=learner.id,
        title=payload.title.strip(),
        skills=payload.skills or [],
    )
    db.add(course)
    incoming = []
    for name in payload.skills:
        if not name.strip():
            continue
        incoming.append(normalize_skill({"name": name, "proficiency": 50, "source": "completed_course", "evidence": [payload.title]}))
    learner.skills = merge_skills(learner.skills or [], [s for s in incoming if s])
    touch_streak(learner)
    db.commit()
    db.refresh(learner)
    return learner


def apply_semester(db: Session, learner: Learner, payload: FromSemesterRequest) -> Learner:
    from app.models import AcademicProfile, AcademicSubject
    from app.services import skill_registry

    incoming = []
    topic_ids = []
    resource_rows = []
    for name in payload.skills:
        if not name or not name.strip():
            continue
        incoming.append(
            normalize_skill(
                {"name": name, "proficiency": 45, "source": "semester", "evidence": [payload.semester or "syllabus"]}
            )
        )
        try:
            resolved = skill_registry.resolve_for_learner(db, learner, name)
            leaves = [
                t
                for t in (resolved.get("topics") or [])
                if "major-" not in str(t.get("id") or "") and not str(t.get("slug") or "").startswith("major-")
            ]
            ids = [t["id"] for t in leaves] or [t["id"] for t in resolved.get("topics") or []]
            topic_ids.extend(ids)
            from app.models import SkillTopic
            from app.services import path_service as path_svc

            topic_objs = [db.get(SkillTopic, tid) for tid in ids[:6]]
            topic_objs = [t for t in topic_objs if t]
            bundled = path_svc.collect_resources_for_topics(db, learner, topic_objs, resolved["skill"]["id"])
            for tid, rows in bundled.items():
                resource_rows.extend([{**r, "topic_id": tid} for r in rows[:3]])
        except HTTPException:
            continue
    learner.skills = merge_skills(learner.skills or [], [s for s in incoming if s])
    if payload.semester:
        interests = list(learner.interests or [])
        tag = f"Semester {payload.semester}" if not str(payload.semester).lower().startswith("semester") else str(payload.semester)
        if tag not in interests:
            interests.append(tag)
            learner.interests = interests
    profile = db.query(AcademicProfile).filter(AcademicProfile.learner_id == learner.id).first()
    if not profile:
        profile = AcademicProfile(learner_id=learner.id, semester=payload.semester or "")
        db.add(profile)
        db.flush()
    else:
        profile.semester = payload.semester or profile.semester
    if payload.skills:
        db.add(AcademicSubject(academic_profile_id=profile.id, subject=", ".join(payload.skills[:8]), topic_ids=topic_ids[:40], resources=resource_rows[:24]))
    db.commit()
    db.refresh(learner)
    return learner


def apply_role_fit(db: Session, learner: Learner, payload: FromRoleFitRequest) -> Learner:
    from app.services import skill_registry

    learner.target_role = payload.target_role.strip()
    gaps = [g.strip() for g in payload.missing_skills if g and g.strip()]
    structured = []
    incoming = []
    for name in payload.strengths:
        if name and name.strip():
            incoming.append(normalize_skill({"name": name, "proficiency": 65, "source": "role_fit"}))
            try:
                skill_registry.resolve_for_learner(db, learner, name)
            except HTTPException:
                pass
    for name in gaps:
        incoming.append(normalize_skill({"name": name, "proficiency": 20, "source": "role_fit"}))
        try:
            resolved = skill_registry.resolve_for_learner(db, learner, name)
            sid = resolved["skill"]["id"]
            enrolled = next((s for s in skill_registry.list_learner_skills(db, learner) if s["id"] == sid), None)
            structured.append(
                {
                    "skill_id": sid,
                    "name": resolved["skill"]["name"],
                    "current": enrolled["overall_proficiency"] if enrolled else 0,
                    "required": 70,
                    "priority": "high",
                }
            )
        except HTTPException:
            structured.append({"skill_id": name.lower().replace(" ", "-"), "name": name, "current": 20, "required": 70, "priority": "high"})
    existing_gaps = []
    for g in learner.skill_gaps or []:
        if isinstance(g, dict) and g.get("skill_id") not in {x["skill_id"] for x in structured}:
            existing_gaps.append(g)
        elif isinstance(g, str) and g.lower() not in {x.lower() for x in gaps}:
            existing_gaps.append(g)
    learner.skill_gaps = structured + existing_gaps
    learner.skills = merge_skills(learner.skills or [], [s for s in incoming if s])
    if payload.target_role and not learner.goal:
        learner.goal = f"Become a {payload.target_role.strip()}"
    try:
        skill_registry.resolve_for_learner(db, learner, payload.target_role)
    except HTTPException:
        apply_required_for_goal(learner)
    db.commit()
    db.refresh(learner)
    return learner
