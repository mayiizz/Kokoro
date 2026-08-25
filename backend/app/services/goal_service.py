import re
from typing import Dict, List

from fastapi import HTTPException

from app.core.groq_client import get_groq_response
from app.services import graph_service


def slugify(name: str) -> str:
    key = (name or "").strip().lower()
    key = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    return key[:80] or "skill"


def parse_schedule(text: str) -> dict:
    blob = (text or "").lower()
    months = None
    hours_per_day = None
    daily_minutes = None
    month_match = re.search(r"(\d+(?:\.\d+)?)\s*months?", blob)
    if month_match:
        months = max(1, int(round(float(month_match.group(1)))))
    hour_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*(?:each\s+|a\s+|per\s+|every\s+)?(?:day|daily)?",
        blob,
    )
    minute_match = re.search(
        r"(\d+)\s*(?:min|minutes)\s*(?:each\s+|a\s+|per\s+|every\s+)?(?:day|daily)?",
        blob,
    )
    if hour_match and "hour" in blob:
        hours_per_day = float(hour_match.group(1))
        daily_minutes = int(round(hours_per_day * 60))
    elif minute_match:
        daily_minutes = int(minute_match.group(1))
        hours_per_day = max(0.25, daily_minutes / 60)
    return {
        "duration_months": months,
        "hours_per_day": hours_per_day,
        "daily_minutes": daily_minutes,
    }


def _normalize_subskills(raw) -> List[dict]:
    rows = []
    seen = set()
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or item.get("skill") or item.get("id") or "").strip()
        if not name:
            continue
        sid = slugify(item.get("id") or name)
        if sid in seen:
            continue
        seen.add(sid)
        prereqs = []
        for p in item.get("prerequisites") or []:
            pid = slugify(p) if isinstance(p, str) else slugify((p or {}).get("id") or "")
            if pid:
                prereqs.append(pid)
        try:
            required = int(item.get("required") or 70)
        except (TypeError, ValueError):
            required = 70
        rows.append(
            {
                "id": sid,
                "name": name,
                "prerequisites": prereqs,
                "required": max(0, min(100, required)),
            }
        )
    return rows[:16]


def _subskills_from_static(skill_ids: List[str]) -> List[dict]:
    index = graph_service.skill_index()
    rows = []
    for sid in skill_ids:
        meta = index.get(sid) or {}
        rows.append(
            {
                "id": sid,
                "name": meta.get("name", sid),
                "prerequisites": list(meta.get("prerequisites") or []),
                "required": int(meta.get("required") or 70),
            }
        )
    return rows


def decompose_goal(goal: str, target_role: str = "", extra: str = "") -> dict:
    blob = f"{target_role} {goal} {extra}".strip()
    static = graph_service.required_skills_for_goal(goal, target_role)
    schedule = parse_schedule(blob)
    if static:
        return {
            "goal": goal.strip(),
            "domain": "tech-catalog",
            "primary_skill": (_subskills_from_static(static)[0]["name"] if static else ""),
            "duration_months": schedule.get("duration_months"),
            "daily_minutes": schedule.get("daily_minutes"),
            "current_level": "beginner",
            "subskills": _subskills_from_static(static),
            "from_catalog": True,
        }
    prompt = f"""
Parse this learning goal and decompose it into domain-specific subskills.

Goal text: {goal}
Target role: {target_role or "none"}
Extra: {extra or "none"}

Return JSON:
{{
  "goal": string,
  "domain": string,
  "primary_skill": string,
  "duration_months": number or null,
  "daily_minutes": number or null,
  "current_level": "beginner" | "intermediate" | "advanced",
  "subskills": [
    {{"id": "kebab-case-id", "name": "Human name", "prerequisites": ["other-id"], "required": 70}}
  ]
}}

Rules:
- Subskills MUST be specific to THIS goal's domain (music, language, sport, cooking, design, trades, etc.).
- Do NOT assume programming, data analysis, JavaScript, Python, SQL, or web development unless the goal is clearly about those.
- 6 to 10 subskills, ordered from foundations to later skills.
- ids are kebab-case. required is 0-100 (typically 65-80).
- Parse duration and daily study time when mentioned (e.g. 5 months, 1 hour a day).
"""
    try:
        data = get_groq_response(prompt)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not parse this goal: {exc}",
        ) from exc
    subskills = _normalize_subskills(data.get("subskills"))
    if not subskills:
        raise HTTPException(
            status_code=502,
            detail="Could not decompose this goal into skills. Try a more specific goal.",
        )
    duration = data.get("duration_months") or schedule.get("duration_months")
    daily = data.get("daily_minutes") or schedule.get("daily_minutes")
    try:
        duration = int(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration = schedule.get("duration_months")
    try:
        daily = int(daily) if daily is not None else None
    except (TypeError, ValueError):
        daily = schedule.get("daily_minutes")
    return {
        "goal": (data.get("goal") or goal).strip(),
        "domain": data.get("domain") or "general",
        "primary_skill": data.get("primary_skill") or subskills[0]["name"],
        "duration_months": duration,
        "daily_minutes": daily,
        "current_level": data.get("current_level") or "beginner",
        "subskills": subskills,
        "from_catalog": False,
    }


def learner_required_ids(learner) -> List[str]:
    subs = getattr(learner, "goal_subskills", None) or []
    ids = [s.get("id") for s in subs if isinstance(s, dict) and s.get("id")]
    if ids:
        return ids
    return graph_service.required_skills_for_goal(learner.goal or "", getattr(learner, "target_role", "") or "")


def skill_defs_for_learner(learner) -> Dict[str, dict]:
    defs: Dict[str, dict] = {}
    for sub in getattr(learner, "goal_subskills", None) or []:
        if not isinstance(sub, dict) or not sub.get("id"):
            continue
        sid = sub["id"]
        defs[sid] = {
            "id": sid,
            "name": sub.get("name") or sid,
            "prerequisites": list(sub.get("prerequisites") or []),
            "required": int(sub.get("required") or 70),
            "importance": 0.7,
        }
    for skill in learner.skills or []:
        if not isinstance(skill, dict):
            continue
        sid = skill.get("skill_id")
        if not sid or sid in defs or sid in graph_service.skill_index():
            continue
        defs[sid] = {
            "id": sid,
            "name": skill.get("name") or sid,
            "prerequisites": [],
            "required": int(skill.get("required") or 70),
            "importance": 0.5,
        }
    return defs


def extra_prereqs(learner) -> Dict[str, List[str]]:
    return {sid: list(meta.get("prerequisites") or []) for sid, meta in skill_defs_for_learner(learner).items()}


def skill_name(learner, skill_id: str) -> str:
    defs = skill_defs_for_learner(learner)
    if skill_id in defs:
        return defs[skill_id]["name"]
    meta = graph_service.skill_index().get(skill_id)
    if meta:
        return meta["name"]
    for skill in learner.skills or []:
        if isinstance(skill, dict) and skill.get("skill_id") == skill_id:
            return skill.get("name") or skill_id
    return skill_id


def ensure_decomposed(learner, extra_text: str = "") -> List[dict]:
    from app.services.learner_service import apply_required_for_goal

    goal = (learner.goal or getattr(learner, "target_role", None) or extra_text or "").strip()
    if not goal:
        return getattr(learner, "goal_subskills", None) or []
    existing = getattr(learner, "goal_subskills", None) or []
    meta = getattr(learner, "goal_meta", None) or {}
    if existing and meta.get("source_goal") == goal:
        apply_required_for_goal(learner)
        return existing
    parsed = decompose_goal(goal, getattr(learner, "target_role", "") or "", extra_text)
    learner.goal_meta = {**parsed, "source_goal": goal}
    learner.goal_subskills = parsed["subskills"]
    if parsed.get("duration_months"):
        learner.duration_months = int(parsed["duration_months"])
    if parsed.get("daily_minutes"):
        mins = int(parsed["daily_minutes"])
        hours = max(1, int(round(mins / 60))) if mins >= 30 else 1
        learner.hours_per_day = hours
        learner.hours_per_week = hours * 7
    apply_required_for_goal(learner)
    return learner.goal_subskills
