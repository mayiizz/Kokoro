from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.groq_client import get_groq_response
from app.models import LearningPath, PathItem
from app.services import catalog_service, gap_service, goal_service, graph_service
from app.services.learner_service import (
    bump_proficiency,
    get_learner_or_404,
    merge_skills,
    touch_streak,
)

PHASES = [
    ("Foundations", {"python", "html", "css", "javascript", "git", "sql", "probability", "linux", "excel", "rest"}),
    ("Core skills", {"numpy", "pandas", "statistics", "react", "typescript", "fastapi", "postgresql", "data-visualization", "data-analysis", "linear-algebra", "nodejs"}),
    ("Applied", {"machine-learning", "scikit-learn", "frontend", "backend", "docker", "algorithms", "accessibility"}),
    ("Advanced", {"deep-learning", "mlops", "system-design", "interviews", "aws"}),
]


def _skill_names(learner) -> List[str]:
    names = []
    for skill in merge_skills(learner.skills or [], []):
        names.append(skill["name"])
    return names


def _completed_titles(learner) -> List[str]:
    return [c.title for c in (learner.completed_courses or [])]


def _active_path(db: Session, learner_id: str, skill_id: str | None = None, strict: bool = False) -> Optional[LearningPath]:
    q = db.query(LearningPath).filter(LearningPath.learner_id == learner_id, LearningPath.status == "active")
    if skill_id:
        match = q.filter(LearningPath.skill_id == skill_id).order_by(LearningPath.created_at.desc()).first()
        if match:
            return match
        if strict:
            return None
    elif strict:
        return None
    return q.order_by(LearningPath.created_at.desc()).first()


def _archive_active(db: Session, learner_id: str, skill_id: str | None = None):
    q = db.query(LearningPath).filter(LearningPath.learner_id == learner_id, LearningPath.status == "active")
    if skill_id:
        q = q.filter(LearningPath.skill_id == skill_id)
    for path in q:
        path.status = "archived"


def _phase_for(skill_id: str) -> str:
    for name, group in PHASES:
        if skill_id in group:
            return name
    return "Core skills"


def _catalog_overlap(skill_ids: List[str]) -> set:
    teaches = set()
    for item in catalog_service.load_catalog():
        teaches.update(item.get("teaches") or [])
    return set(skill_ids) & teaches


def _why(learner, skill_id: str, item: dict, db: Session = None) -> str:
    gaps = {g["skill_id"]: g for g in gap_service.compute_gaps(learner, db)}
    row = gaps.get(skill_id)
    name = item.get("skill_name") or goal_service.skill_name(learner, skill_id)
    if row:
        return (
            f"You're learning {name} now because proficiency is {row['current']}% "
            f"versus about {row['required']}% required for your goal. "
            f"{item.get('title')} is a {item.get('cost', 'free')} {item.get('format') or ''} {item.get('type')} "
            f"that fits that gap."
        )
    if item.get("why"):
        return item["why"]
    return f"{item.get('title')} teaches {name}."


def _best_for_skill(learner, skill_id: str, catalog: List[dict], used: set, prefer_type: Optional[str] = None) -> Optional[dict]:
    proficiency = 0
    for s in merge_skills(learner.skills or [], []):
        if s["skill_id"] == skill_id:
            proficiency = s["proficiency"]
            break
    preference = learner.learning_preference or "hands-on"
    budget = getattr(learner, "budget", None) or "free"
    hours = getattr(learner, "hours_per_day", None) or 2
    scored = []
    for item in catalog:
        if item["id"] in used:
            continue
        if prefer_type and item.get("type") != prefer_type:
            continue
        if skill_id not in (item.get("teaches") or []):
            continue
        score = catalog_service.rank_resource(
            item,
            skill_id=skill_id,
            proficiency=proficiency,
            preference=preference,
            budget=budget,
            hours_per_day=hours,
        )
        scored.append((score, item))
    if not scored and prefer_type:
        return _best_for_skill(learner, skill_id, catalog, used, prefer_type=None)
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def _resources_for_topic(learner, topic, catalog: List[dict], used: set) -> List[dict]:
    from app.services.skill_registry import catalog_keys_for_topic

    keys = set(catalog_keys_for_topic(topic))
    scored = []
    for item in catalog:
        teaches = set(item.get("teaches") or [])
        names = {str(s).lower() for s in (item.get("skills") or [])}
        if not (keys & teaches) and topic.slug not in teaches and topic.name.lower() not in names:
            continue
        if item["id"] in used:
            continue
        score = catalog_service.rank_resource(
            item,
            skill_id=topic.slug or topic.id,
            proficiency=0,
            preference=learner.learning_preference or "hands-on",
            budget=getattr(learner, "budget", None) or "free",
            hours_per_day=getattr(learner, "hours_per_day", None) or 2,
        )
        scored.append((score, item))
    scored.sort(key=lambda x: -x[0])
    picked = []
    for _, item in scored[:4]:
        used.add(item["id"])
        picked.append(
            {
                "title": item.get("title"),
                "url": item.get("url") or "",
                "type": item.get("type") or "course",
                "rank": len(picked) + 1,
                "why": f"Ranked for {topic.name} ({item.get('cost', 'free')} {item.get('format', '')} {item.get('type')}).",
                "about": (item.get("description") or f"{item.get('title')} covers {topic.name} as a {item.get('type') or 'course'}.").strip(),
            }
        )
    return picked


def _ensure_resource_floor(item: dict) -> None:
    from app.services import resource_links

    resources = list(item.get("resources") or [])
    name = item.get("skill_name") or item.get("title") or "this topic"
    skill_id = item.get("skill_id") or ""
    resources = resource_links.normalize_resources(resources, topic_name=name, skill_id=skill_id)
    while len(resources) < 2:
        kind = "video" if len(resources) == 0 else "website"
        resources.append(
            {
                "title": f"{name} {kind}",
                "url": resource_links.search_fallback(name, kind, name),
                "type": kind,
                "rank": len(resources) + 1,
                "why": f"Public {kind} practice for {name} while a catalog match is missing.",
                "about": f"Working search results for {name} {kind}s.",
            }
        )
        resources = resource_links.normalize_resources(resources, topic_name=name, skill_id=skill_id)
    item["resources"] = resources[:4]
    if resources:
        if not item.get("url") or resource_links.looks_broken(item.get("url") or ""):
            item["url"] = resources[0]["url"]
        if not item.get("title") or str(item.get("title") or "").startswith("Learn "):
            item["title"] = resources[0]["title"]


def build_sequence(db: Session, learner, skip_skills: Optional[List[str]] = None, focus_skills: Optional[List[str]] = None) -> List[dict]:
    from app.services import skill_registry

    skip = set(skip_skills or [])
    focus = set(focus_skills or [])
    skill_registry.seed_catalog_skills(db)
    sid = skill_registry.active_skill_id(learner, db)
    if not sid and (learner.goal or learner.target_role):
        try:
            skill_registry.resolve_for_learner(db, learner, learner.goal or learner.target_role)
            sid = skill_registry.active_skill_id(learner, db)
        except HTTPException:
            pass
    if sid:
        skill_registry.ensure_learner_skill(db, learner, sid)
        topics = skill_registry.weak_topics(db, learner, sid, skip_ids=skip, focus_ids=focus)
        if not topics:
            topics = skill_registry.leaf_topics_for_skill(db, sid)[:8]
        catalog = catalog_service.filter_candidates(
            experience_level=learner.experience_level or "Student",
            completed_titles=_completed_titles(learner),
            budget=getattr(learner, "budget", None) or "free",
        )
        used = set()
        items: List[dict] = []
        week = 1
        need_llm = []
        from app.models import SkillTopic as SkillTopicModel

        for i, topic in enumerate(topics[:12]):
            resources = _resources_for_topic(learner, topic, catalog, used)
            if len(resources) < 2:
                need_llm.append(topic)
            primary = resources[0] if resources else None
            title = primary["title"] if primary else f"Learn {topic.name}"
            url = primary["url"] if primary else ""
            parent = db.get(SkillTopicModel, topic.parent_id) if topic.parent_id else None
            phase = parent.name if parent else "Core"
            items.append(
                {
                    "catalog_id": (primary and f"cat-{goal_service.slugify(primary['title'])}") or f"topic-{topic.id}",
                    "item_type": (primary or {}).get("type") or "course",
                    "skill_id": sid,
                    "skill_name": topic.name,
                    "topic_id": topic.id,
                    "title": title,
                    "url": url,
                    "phase": phase,
                    "week": week,
                    "why": f"You're covering {topic.name} because it is not yet at the required proficiency for this skill.",
                    "milestone_title": topic.name,
                    "prereq_ids": topic.prerequisites or [],
                    "resources": resources,
                }
            )
            if (i + 1) % 3 == 0:
                week += 1
        if need_llm:
            llm_map = _llm_resources_for_topics(learner, sid, need_llm)
            for item in items:
                extra = llm_map.get(item["topic_id"]) or []
                merged = list(item.get("resources") or [])
                seen = {r.get("url") or r.get("title") for r in merged}
                for row in extra:
                    key = row.get("url") or row.get("title")
                    if key in seen:
                        continue
                    merged.append(row)
                    seen.add(key)
                item["resources"] = merged[:4]
                if merged and (not item.get("url") or str(item.get("title") or "").startswith("Learn ")):
                    item["title"] = merged[0]["title"]
                    item["url"] = merged[0].get("url") or item.get("url") or ""
        for item in items:
            _ensure_resource_floor(item)
        return items[:12]

    try:
        goal_service.ensure_decomposed(learner)
    except HTTPException:
        pass
    gaps = gap_service.compute_gaps(learner, db)
    extra_prereqs = goal_service.extra_prereqs(learner)
    required_ids = goal_service.learner_required_ids(learner)
    ordered = graph_service.ordered_skills(required_ids, extra_prereqs=extra_prereqs)
    gap_map = {g["skill_id"]: g for g in gaps}

    open_skills = []
    for oid in ordered:
        row = gap_map.get(oid)
        if oid in skip:
            continue
        if row and row["gap"] <= 0 and oid not in focus:
            continue
        open_skills.append(oid)
    if focus:
        open_skills = ordered_unique(list(focus) + open_skills)

    overlap = _catalog_overlap(open_skills or required_ids)
    if not overlap:
        return _llm_sequence(learner, open_skills or required_ids)[:16]

    catalog = catalog_service.filter_candidates(
        skill_ids=open_skills,
        experience_level=learner.experience_level or "Student",
        completed_titles=_completed_titles(learner),
        budget=getattr(learner, "budget", None) or "free",
    )
    used = set()
    items = []
    skills_since_project = 0
    hours_per_day = getattr(learner, "hours_per_day", None) or 2
    week_budget = max(hours_per_day, 1) * 7
    week = 1
    week_hours = 0

    for oid in open_skills:
        course = _best_for_skill(learner, oid, catalog, used, prefer_type="course")
        if not course:
            course = _best_for_skill(learner, oid, catalog, used)
        if not course:
            continue
        used.add(course["id"])
        hours = int(course.get("hours") or 4)
        if week_hours + hours > week_budget and week_hours > 0:
            week += 1
            week_hours = 0
        week_hours += hours
        items.append(_item_dict(learner, course, oid, week, skills_since_project))
        skills_since_project += 1

        if skills_since_project >= 2:
            project = _best_for_skill(learner, oid, catalog, used, prefer_type="project")
            if project:
                used.add(project["id"])
                items.append(_item_dict(learner, project, oid, week, skills_since_project, force_type="project"))
                skills_since_project = 0
            assess = _best_for_skill(learner, oid, catalog, used, prefer_type="assessment")
            if assess:
                used.add(assess["id"])
                items.append(_item_dict(learner, assess, oid, week, 0, force_type="assessment"))

    if not items:
        for cand in catalog[:10]:
            oid = (cand.get("teaches") or [open_skills[0] if open_skills else ""])[0]
            items.append(_item_dict(learner, cand, oid, 1, 0))
    return items[:16]


def _llm_resources_for_topics(learner, skill_id: str, topics) -> dict:
    from app.services import resource_agent

    if resource_agent.has_tavily() and topics:
        found = resource_agent.find_resources(learner, skill_id, topics)
        if any(found.values()):
            return found
    blob = ", ".join(f"{t.id} ({t.name})" for t in topics)
    prompt = f"""
JSON resources for these topics. Skill: {skill_id}. Goal: {learner.goal}.
Topics: {blob}
{{"resources":[{{"topic_id":"...","title":"...","url":"https://...","type":"course|video|textbook|website","about":"1-2 sentences on what this covers","why":"..."}}]}}
2 to 4 resources per topic. Mix types: official course, YouTube video, textbook product page, reference website.
Rules:
- url MUST be a real public https page that exists today. Never invent YouTube video IDs, Amazon ASINs, or lesson slugs.
- Prefer official sites (justinguitar.com, andyguitar.co.uk, musictheory.net, hal Leonard, MDN, freeCodeCamp).
- For YouTube, use channel URLs (youtube.com/@Name) or youtube.com/results?search_query=... if you are not certain of a video ID.
- Not programming unless the skill is software.
"""
    try:
        data = get_groq_response(prompt)
    except Exception:
        return {}
    out = {}
    def _tid(raw: str, index: int) -> str:
        key = (raw or "").strip()
        for topic in topics:
            slug = topic.slug or topic.id
            if key in (topic.id, slug) or topic.id.endswith(f"--{key}") or key.endswith(slug):
                return topic.id
        return topics[index % len(topics)].id if topics else key

    for i, row in enumerate(data.get("resources") or []):
        if not isinstance(row, dict) or not row.get("title"):
            continue
        tid = _tid(str(row.get("topic_id") or row.get("skill_id") or ""), i)
        type_raw = str(row.get("type") or "website").lower()
        if type_raw in ("article", "docs", "reference"):
            type_raw = "website"
        if type_raw in ("youtube", "lesson"):
            type_raw = "video"
        if type_raw not in ("course", "video", "textbook", "website", "project"):
            type_raw = "website"
        out.setdefault(tid, []).append(
            {
                "title": row["title"],
                "url": row.get("url") or "",
                "type": type_raw,
                "rank": len(out.get(tid, [])) + 1,
                "why": row.get("why") or "",
                "about": str(row.get("about") or row.get("why") or f"{row['title']} helps you learn this topic."),
            }
        )
    from app.services import resource_links

    return {
        tid: resource_links.normalize_resources(rows, topic_name=next((t.name for t in topics if t.id == tid), tid), skill_id=skill_id)
        for tid, rows in out.items()
    }


def collect_resources_for_topics(db: Session, learner, topics, skill_id: str) -> dict:
    catalog = catalog_service.filter_candidates(
        experience_level=learner.experience_level or "Student",
        completed_titles=_completed_titles(learner),
        budget=getattr(learner, "budget", None) or "free",
    )
    used = set()
    bundled = {}
    need_llm = []
    for topic in topics:
        resources = _resources_for_topic(learner, topic, catalog, used)
        if len(resources) < 2:
            need_llm.append(topic)
        bundled[topic.id] = resources
    if need_llm:
        llm_map = _llm_resources_for_topics(learner, skill_id, need_llm)
        for topic in need_llm:
            merged = list(bundled.get(topic.id) or [])
            seen = {r.get("url") or r.get("title") for r in merged}
            for row in llm_map.get(topic.id) or []:
                key = row.get("url") or row.get("title")
                if key in seen:
                    continue
                merged.append(row)
                seen.add(key)
            bundled[topic.id] = merged[:4]
    out = {}
    for topic in topics:
        stub = {"resources": bundled.get(topic.id) or [], "skill_name": topic.name, "title": f"Learn {topic.name}"}
        _ensure_resource_floor(stub)
        out[topic.id] = stub["resources"]
    return out


def ordered_unique(ids: List[str]) -> List[str]:
    seen = []
    for i in ids:
        if i not in seen:
            seen.append(i)
    return graph_service.ordered_skills(seen)


def _item_dict(learner, catalog_item: dict, skill_id: str, week: int, _idx: int, force_type: str = None) -> dict:
    item_type = force_type or catalog_item.get("type", "course")
    phase = catalog_item.get("phase") or _phase_for(skill_id)
    milestone = ""
    if item_type in ("project", "assessment"):
        milestone = f"{phase}: {catalog_item.get('title', '')}"
    return {
        "catalog_id": catalog_item.get("id") or f"llm-{goal_service.slugify(catalog_item.get('title') or skill_id)}",
        "item_type": item_type,
        "skill_id": skill_id,
        "skill_name": catalog_item.get("skill_name") or goal_service.skill_name(learner, skill_id),
        "title": catalog_item.get("title") or "",
        "url": catalog_item.get("url") or "",
        "phase": phase,
        "week": week,
        "why": catalog_item.get("why") or _why(learner, skill_id, catalog_item),
        "milestone_title": milestone,
        "prereq_ids": catalog_item.get("prereq_ids") or [],
    }


def _llm_sequence(learner, skill_ids: List[str]) -> List[dict]:
    duration = getattr(learner, "duration_months", None) or 3
    hours = getattr(learner, "hours_per_day", None) or 1
    subskills = getattr(learner, "goal_subskills", None) or []
    skill_blob = ", ".join(
        f"{s.get('id')} ({s.get('name')})" for s in subskills if isinstance(s, dict)
    ) or ", ".join(skill_ids)
    prompt = f"""
Month-by-month plan as JSON. Goal: {learner.goal or learner.target_role}. {duration} months, {hours} h/day.
Skills: {skill_blob}
{{"resources":[{{"month":1,"title":"...","url":"https://...","type":"course","skill_id":"id","skill_name":"...","why":"..."}}]}}
8-12 real public resources. Not programming unless the goal is software.
"""
    try:
        data = get_groq_response(prompt)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not build a path for this goal: {exc}",
        ) from exc
    raw = data.get("resources") or []
    if not raw and isinstance(data.get("plan"), list):
        for month in data["plan"]:
            for row in month.get("resources") or []:
                raw.append({**row, "month": month.get("month") or 1})
    if not raw:
        raise HTTPException(status_code=502, detail="Could not build a path for this goal. Try again.")
    items = []
    used_ids = set()
    for i, row in enumerate(raw):
        if not isinstance(row, dict) or not row.get("title"):
            continue
        month = int(row.get("month") or (i // 2) + 1)
        sid = goal_service.slugify(row.get("skill_id") or row.get("skill_name") or (skill_ids[i % len(skill_ids)] if skill_ids else "skill"))
        cid = f"llm-{goal_service.slugify(row['title'])}"
        if cid in used_ids:
            cid = f"{cid}-{i}"
        used_ids.add(cid)
        catalog_like = {
            "id": cid,
            "title": row["title"],
            "url": row.get("url") or "",
            "type": row.get("type") or "course",
            "skill_name": row.get("skill_name") or goal_service.skill_name(learner, sid),
            "phase": f"Month {month}",
            "why": row.get("why") or "",
        }
        items.append(_item_dict(learner, catalog_like, sid, max(1, month * 4), i))
    return items[:16]


def _persist_items(db: Session, path: LearningPath, items: List[dict], start_order: int = 1):
    for i, item in enumerate(items):
        db.add(
            PathItem(
                path_id=path.id,
                catalog_id=item["catalog_id"],
                order=start_order + i,
                item_type=item.get("item_type") or "course",
                title=item.get("title") or "",
                url=item.get("url") or "",
                skill_id=item.get("skill_id") or "",
                skill_name=item.get("skill_name") or "",
                topic_id=item.get("topic_id") or "",
                resources=item.get("resources") or [],
                phase=item.get("phase") or "",
                week=int(item.get("week") or 1),
                milestone_title=item.get("milestone_title") or "",
                prereq_ids=item.get("prereq_ids") or [],
                why=item.get("why") or "",
                status="todo",
            )
        )


def serialize_path(path: Optional[LearningPath]) -> Optional[dict]:
    if not path:
        return None
    catalog = catalog_service.catalog_index()
    done_ids = {i.catalog_id for i in path.items if i.status == "done"}
    done_topics = {getattr(i, "topic_id", "") for i in path.items if i.status == "done" and getattr(i, "topic_id", "")}
    serialized_items = []
    for item in sorted(path.items, key=lambda x: x.order):
        meta = catalog.get(item.catalog_id) or {}
        prereqs_met = all(p in done_ids or p in done_topics for p in (item.prereq_ids or []))
        locked = item.status == "todo" and not prereqs_met
        serialized_items.append(
            {
                "id": item.id,
                "catalog_id": item.catalog_id,
                "order": item.order,
                "item_type": item.item_type,
                "skill_id": getattr(item, "skill_id", "") or "",
                "topic_id": getattr(item, "topic_id", "") or "",
                "resources": getattr(item, "resources", None) or [],
                "phase": getattr(item, "phase", "") or _phase_for(getattr(item, "skill_id", "") or ""),
                "week": getattr(item, "week", None) or 1,
                "title": getattr(item, "title", "") or meta.get("title") or item.catalog_id,
                "provider": meta.get("provider", ""),
                "url": getattr(item, "url", "") or meta.get("url", ""),
                "hours": meta.get("hours", 0),
                "level": meta.get("level", ""),
                "cost": meta.get("cost", "free"),
                "format": meta.get("format", ""),
                "skills": meta.get("skills") or ([getattr(item, "skill_name", "") or item.skill_id] if getattr(item, "skill_id", "") else []),
                "description": meta.get("description", ""),
                "milestone_title": item.milestone_title or "",
                "prereq_ids": item.prereq_ids or [],
                "why": item.why or "",
                "status": item.status,
                "feedback": item.feedback or "",
                "locked": locked,
            }
        )
    next_action = next((i for i in serialized_items if i["status"] == "todo" and not i["locked"]), None)
    phases: Dict[str, list] = defaultdict(list)
    for row in serialized_items:
        phases[row["phase"] or "Path"].append(row)
    return {
        "id": path.id,
        "learner_id": path.learner_id,
        "goal": path.goal,
        "status": path.status,
        "skill_id": getattr(path, "skill_id", "") or "",
        "items": serialized_items,
        "phases": [{"name": k, "items": v} for k, v in phases.items()],
        "next_action": next_action,
    }


def generate_path(db: Session, learner_id: str) -> dict:
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    items = build_sequence(db, learner)
    sid = skill_registry.active_skill_id(learner, db)
    _archive_active(db, learner_id, sid)
    path = LearningPath(
        learner_id=learner.id,
        skill_id=sid,
        goal=learner.goal or learner.target_role or "",
        status="active",
    )
    db.add(path)
    db.flush()
    _persist_items(db, path, items)
    db.commit()
    db.refresh(path)
    return serialize_path(path)


def adapt_path(db: Session, learner_id: str, skip_skills=None, focus_skills=None) -> dict:
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    sid = skill_registry.active_skill_id(learner, db)
    path = _active_path(db, learner_id, sid, strict=True)
    if not path:
        return generate_path(db, learner_id)
    kept = [i for i in path.items if i.status in ("done", "skipped") or i.feedback == "helpful"]
    exclude = {i.catalog_id for i in path.items if i.feedback in ("too_hard", "not_relevant") or i.status == "done"}
    for item in list(path.items):
        if item not in kept:
            db.delete(item)
    db.flush()
    remaining = [it for it in build_sequence(db, learner, skip_skills=skip_skills, focus_skills=focus_skills) if it["catalog_id"] not in exclude]
    # skip intro courses for skip_skills
    if skip_skills:
        remaining = [it for it in remaining if not (it.get("skill_id") in skip_skills and it.get("item_type") == "course")]
    start = max((i.order for i in kept), default=0) + 1
    _persist_items(db, path, remaining, start_order=start)
    db.commit()
    db.refresh(path)
    return serialize_path(path)


def replan_from_assessment(db: Session, learner_id: str, skip_skills: List[str], focus_skills: List[str]) -> Optional[dict]:
    path = _active_path(db, learner_id)
    if not path:
        return generate_path(db, learner_id)
    return adapt_path(db, learner_id, skip_skills=skip_skills, focus_skills=focus_skills)


def _repair_path_resources(db: Session, path: Optional[LearningPath]) -> None:
    from app.services import resource_links

    if not path:
        return
    changed = False
    for item in path.items:
        rows = list(getattr(item, "resources", None) or [])
        topic = getattr(item, "skill_name", "") or item.title
        skill_id = getattr(item, "skill_id", "") or ""
        fixed = resource_links.normalize_resources(rows, topic_name=topic, skill_id=skill_id)
        if [r.get("url") for r in rows] != [r.get("url") for r in fixed]:
            item.resources = fixed
            changed = True
        current = getattr(item, "url", "") or ""
        if fixed and (not current or resource_links.looks_broken(current)):
            item.url = fixed[0]["url"]
            changed = True
    if changed:
        db.commit()


def get_path(db: Session, learner_id: str) -> Optional[dict]:
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    sid = skill_registry.active_skill_id(learner, db)
    path = _active_path(db, learner_id, sid, strict=True)
    _repair_path_resources(db, path)
    return serialize_path(path)


def more_resources_for_topic(db: Session, learner_id: str, topic_id: str) -> dict:
    from app.models import SkillTopic
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    topic = db.get(SkillTopic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    path = _active_path(db, learner_id, skill_registry.active_skill_id(learner, db), strict=True)
    if not path:
        raise HTTPException(status_code=404, detail="Generate a path for this skill first.")
    item = next((i for i in path.items if getattr(i, "topic_id", "") == topic_id), None)
    existing = list(getattr(item, "resources", None) or []) if item else []
    exclude = {r.get("url") or r.get("title") for r in existing if isinstance(r, dict)}
    llm_map = _llm_resources_for_topics(learner, topic.skill_id, [topic])
    extra = []
    from app.services import resource_links

    for row in resource_links.normalize_resources(llm_map.get(topic.id) or [], topic_name=topic.name, skill_id=topic.skill_id):
        key = row.get("url") or row.get("title")
        if key in exclude:
            continue
        extra.append(row)
        exclude.add(key)
    if not extra:
        stub = {
            "catalog_id": "",
            "title": f"Learn {topic.name}",
            "skill_name": topic.name,
            "resources": existing,
        }
        _ensure_resource_floor(stub)
        extra = [r for r in stub["resources"] if (r.get("url") or r.get("title")) not in exclude]
    merged = existing + extra
    for i, row in enumerate(merged):
        row["rank"] = i + 1
    if item:
        item.resources = merged[:8]
        if extra and extra[0].get("url") and not item.url:
            item.url = extra[0]["url"]
            item.title = extra[0]["title"]
        db.commit()
        db.refresh(path)
    return serialize_path(path)


def patch_item(db: Session, item_id: str, status: Optional[str], feedback: Optional[str]) -> dict:
    item = db.get(PathItem, item_id)
    if not item:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Path item not found")
    learner = item.path.learner
    if status:
        item.status = status
        if status == "done":
            item.completed_at = datetime.utcnow()
            skill_id = getattr(item, "skill_id", "") or ""
            delta = 12 if item.item_type == "project" else (8 if item.item_type == "assessment" else 6)
            cap = 88 if item.item_type != "project" else 92
            if skill_id:
                bump_proficiency(learner, skill_id, delta, f"completed:{item.catalog_id}", cap=cap)
            topic_id = getattr(item, "topic_id", "") or ""
            if topic_id:
                from app.services import skill_registry

                skill_registry.bump_topic(db, learner, topic_id, delta)
            touch_streak(learner)
        if status == "skipped":
            item.completed_at = datetime.utcnow()
    if feedback:
        item.feedback = feedback
        if feedback in ("too_hard", "not_relevant") and item.status == "todo":
            item.status = "skipped"
    db.commit()
    learner_id = item.path.learner_id
    if feedback in ("too_hard", "not_relevant"):
        focus = [item.skill_id] if getattr(item, "skill_id", "") else None
        return adapt_path(db, learner_id, focus_skills=focus)
    return serialize_path(item.path)


def dashboard_for(db: Session, learner_id: str) -> dict:
    from app.services.learner_service import learner_to_dict
    from app.services import skill_registry

    learner = get_learner_or_404(db, learner_id)
    enrolled = skill_registry.list_learner_skills(db, learner)
    if not enrolled and (learner.goal or learner.target_role):
        try:
            skill_registry.resolve_for_learner(db, learner, learner.goal or learner.target_role)
            db.refresh(learner)
            enrolled = skill_registry.list_learner_skills(db, learner)
        except Exception:
            enrolled = skill_registry.list_learner_skills(db, learner)
    sid = skill_registry.active_skill_id(learner, db)
    path = serialize_path(_active_path(db, learner_id, sid, strict=True))
    items = (path or {}).get("items") or []
    done = [i for i in items if i["status"] == "done"]
    projects = [i for i in items if i["item_type"] == "project"]
    projects_done = [i for i in projects if i["status"] == "done"]
    milestones = [i for i in items if i.get("milestone_title")]
    milestones_done = [i for i in milestones if i["status"] == "done"]
    skills = merge_skills(learner.skills or [], [])
    active = next((s for s in enrolled if s["id"] == sid), None)
    skill_cards = []
    for s in enrolled:
        skill_path = serialize_path(_active_path(db, learner_id, s["id"], strict=True))
        skill_items = (skill_path or {}).get("items") or []
        skill_done = [i for i in skill_items if i["status"] == "done"]
        nxt = (skill_path or {}).get("next_action")
        skill_cards.append(
            {
                **s,
                "next_title": nxt["title"] if nxt else None,
                "items_done": len(skill_done),
                "items_total": len(skill_items),
                "path_progress_percent": round(100 * len(skill_done) / len(skill_items)) if skill_items else 0,
            }
        )
    mastered = [s for s in enrolled if s.get("status") == "proficient"] or [s for s in skills if s["proficiency"] >= s.get("required", 70)]
    gaps = gap_service.compute_gaps(learner, db)
    topic_bars = [
        {
            "name": g["name"],
            "skill_id": g.get("skill_id") or g.get("topic_id"),
            "proficiency": g["current"],
            "required": g["required"],
            "source": "topic",
        }
        for g in gaps
    ]
    next_skill = next((g for g in gaps if g["gap"] > 0), None)
    recent = sorted(
        [i for i in items if i["status"] in ("done", "skipped")],
        key=lambda x: x["order"],
        reverse=True,
    )[:5]
    total = len(items) or 1
    return {
        "learner": learner_to_dict(learner),
        "path": path,
        "path_for_active_skill": bool(path),
        "enrolled_skills": skill_cards,
        "active_skill_id": sid or "",
        "active_skill": active,
        "skills_count": len(enrolled) or len(skills),
        "skills": [s.get("name") for s in enrolled] or [s["name"] for s in skills],
        "skill_bars": topic_bars[:12] or skills,
        "skills_mastered": len(mastered),
        "skills_total": max(len(enrolled) or len(gaps), 1),
        "path_progress_percent": round(100 * len(done) / total) if items else 0,
        "items_done": len(done),
        "items_total": len(items),
        "projects_done": len(projects_done),
        "projects_total": len(projects),
        "milestones_done": len(milestones_done),
        "milestones_total": len(milestones),
        "streak_days": getattr(learner, "streak_days", 0) or 0,
        "last_active_date": getattr(learner, "last_active_date", "") or "",
        "next_action": (path or {}).get("next_action"),
        "next_skill": next_skill,
        "recent_completions": recent,
        "goal": learner.goal or "",
        "target_role": learner.target_role or "",
        "gaps": gaps[:12],
        "badges": _badges(mastered, projects_done, getattr(learner, "streak_days", 0) or 0),
    }


def _badges(mastered, projects_done, streak: int) -> List[str]:
    badges = []
    for s in mastered:
        badges.append(f"{s['name']} checkpoint")
    if projects_done:
        badges.append(f"{len(projects_done)} project(s) shipped")
    if streak >= 3:
        badges.append(f"{streak}-day streak")
    return badges[:6]
