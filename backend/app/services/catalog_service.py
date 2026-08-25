import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

from app.services import graph_service

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"

LEVEL_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}
LEARNER_LEVEL = {
    "student": 0,
    "beginner": 0,
    "fresher": 1,
    "intermediate": 1,
    "experienced": 2,
    "advanced": 2,
}

READING_PROVIDERS = {
    "mdn", "git", "w3c wai", "typescript", "numpy", "scikit-learn",
    "fastapi", "restfulapi.net", "postgresql tutorial", "linuxcommand.org",
    "github", "py4e", "css-tricks",
}


def _enrich(item: dict) -> dict:
    row = dict(item)
    row.setdefault("cost", "free")
    row.setdefault("quality", 4)
    provider = (row.get("provider") or "").lower()
    if row.get("type") in ("project", "assessment"):
        row.setdefault("format", "hands-on")
    elif provider in READING_PROVIDERS:
        row.setdefault("format", "reading")
    else:
        row.setdefault("format", "video")
    teaches = row.get("teaches") or []
    if not teaches:
        for name in row.get("skills") or []:
            sid = graph_service.resolve_id(name)
            if sid and sid not in teaches:
                teaches.append(sid)
        row["teaches"] = teaches
    return row


@lru_cache(maxsize=1)
def load_catalog() -> List[dict]:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return [_enrich(item) for item in raw]


def get_by_id(catalog_id: str) -> Optional[dict]:
    for item in load_catalog():
        if item["id"] == catalog_id:
            return item
    return None


def catalog_index() -> dict:
    return {item["id"]: item for item in load_catalog()}


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def filter_candidates(
    *,
    skill_ids: Optional[Iterable[str]] = None,
    skill_names: Iterable[str] = (),
    skill_gaps: Iterable[str] = (),
    experience_level: str = "Student",
    completed_titles: Iterable[str] = (),
    exclude_ids: Optional[Iterable[str]] = None,
    budget: str = "any",
    max_level_delta: int = 1,
) -> List[dict]:
    needed_ids = {s for s in (skill_ids or []) if s}
    needed_names = {_norm(s) for s in list(skill_names) + list(skill_gaps) if s}
    completed = {_norm(t) for t in completed_titles}
    excluded = set(exclude_ids or [])
    learner_rank = LEARNER_LEVEL.get(_norm(experience_level), 0)

    results = []
    for item in load_catalog():
        if item["id"] in excluded:
            continue
        if budget == "free" and item.get("cost") == "paid":
            continue
        if _norm(item["title"]) in completed:
            continue
        item_rank = LEVEL_RANK.get(item.get("level", "beginner"), 0)
        if item_rank > learner_rank + max_level_delta:
            continue
        teaches = set(item.get("teaches") or [])
        item_skills = {_norm(s) for s in item.get("skills", [])}
        overlap_ids = len(teaches & needed_ids) if needed_ids else 0
        overlap_names = len(item_skills & needed_names) if needed_names else 0
        if needed_ids or needed_names:
            if overlap_ids == 0 and overlap_names == 0 and item_rank > learner_rank:
                continue
        scored = dict(item)
        scored["_overlap"] = overlap_ids or overlap_names
        results.append(scored)

    results.sort(key=lambda x: (-x["_overlap"], LEVEL_RANK.get(x.get("level", "beginner"), 0)))
    return results


def rank_resource(item: dict, *, skill_id: str, proficiency: int, preference: str, budget: str, hours_per_day: float) -> float:
    teaches = item.get("teaches") or []
    skill_match = 3.0 if skill_id in teaches else (1.0 if graph_service.resolve_id((item.get("skills") or [""])[0]) == skill_id else 0.0)
    if proficiency < 40:
        want = "beginner"
    elif proficiency < 70:
        want = "intermediate"
    else:
        want = "advanced"
    level = item.get("level", "beginner")
    want_rank = LEVEL_RANK.get(want, 0)
    have_rank = LEVEL_RANK.get(level, 0)
    difficulty_fit = 2.0 if level == want else (1.0 if abs(have_rank - want_rank) == 1 else 0.0)
    pref = (preference or "hands-on").lower()
    fmt = (item.get("format") or "").lower()
    pref_fit = 2.0 if (
        (pref in ("hands-on", "visual") and fmt in ("hands-on", "video") and pref != "reading")
        or (pref == "reading" and fmt == "reading")
        or (pref == "visual" and fmt == "video")
        or (pref == "hands-on" and fmt == "hands-on")
    ) else 0.5
    if pref == "hands-on" and fmt == "hands-on":
        pref_fit = 2.0
    cost_fit = 1.0 if budget != "free" or item.get("cost", "free") == "free" else 0.0
    hours = float(item.get("hours") or 1)
    time_fit = 1.0 if hours <= max(hours_per_day, 1) * 7 else 0.3
    project_bonus = 1.0 if item.get("type") == "project" else 0.0
    quality = float(item.get("quality") or 3) / 5.0
    return skill_match + difficulty_fit + pref_fit + cost_fit + time_fit + project_bonus + quality
