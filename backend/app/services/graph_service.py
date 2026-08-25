import json
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional

SKILLS_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"

ALIASES = {
    "html": "html",
    "css": "css",
    "javascript": "javascript",
    "js": "javascript",
    "dom": "javascript",
    "git": "git",
    "github": "git",
    "version control": "git",
    "accessibility": "accessibility",
    "aria": "accessibility",
    "react": "react",
    "redux": "react",
    "frontend": "frontend",
    "typescript": "typescript",
    "python": "python",
    "numpy": "numpy",
    "pandas": "pandas",
    "sql": "sql",
    "databases": "sql",
    "excel": "excel",
    "spreadsheets": "excel",
    "statistics": "statistics",
    "probability": "probability",
    "linear algebra": "linear-algebra",
    "data visualization": "data-visualization",
    "d3": "data-visualization",
    "data analysis": "data-analysis",
    "machine learning": "machine-learning",
    "ml": "machine-learning",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "deep learning": "deep-learning",
    "pytorch": "deep-learning",
    "tensorflow": "deep-learning",
    "neural networks": "deep-learning",
    "mlops": "mlops",
    "rest": "rest",
    "apis": "rest",
    "http": "rest",
    "fastapi": "fastapi",
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "linux": "linux",
    "cli": "linux",
    "docker": "docker",
    "containers": "docker",
    "aws": "aws",
    "cloud": "aws",
    "backend": "backend",
    "algorithms": "algorithms",
    "data structures": "algorithms",
    "problem solving": "algorithms",
    "interviews": "interviews",
    "career": "interviews",
    "system design": "system-design",
    "scalability": "system-design",
    "web design": "css",
    "flexbox": "css",
    "layout": "css",
    "devops": "docker",
}

GOAL_SKILLS = {
    "ml engineer": [
        "python", "numpy", "pandas", "statistics", "probability",
        "linear-algebra", "machine-learning", "deep-learning", "mlops",
    ],
    "machine learning": [
        "python", "numpy", "pandas", "statistics", "probability", "machine-learning",
    ],
    "data scientist": [
        "python", "numpy", "pandas", "sql", "statistics", "probability",
        "machine-learning", "data-visualization",
    ],
    "data analyst": [
        "python", "sql", "excel", "statistics", "pandas", "data-visualization", "data-analysis",
    ],
    "frontend": ["html", "css", "javascript", "git", "react", "typescript", "accessibility"],
    "frontend developer": ["html", "css", "javascript", "git", "react", "typescript", "accessibility"],
    "backend": ["python", "git", "rest", "sql", "postgresql", "fastapi", "linux", "docker"],
    "backend developer": ["python", "git", "rest", "sql", "postgresql", "fastapi", "linux", "docker"],
    "full stack": ["html", "css", "javascript", "react", "python", "sql", "git", "rest", "fastapi"],
    "ai": [
        "python", "numpy", "pandas", "statistics", "probability",
        "linear-algebra", "machine-learning", "deep-learning",
    ],
}


@lru_cache(maxsize=1)
def load_skills() -> List[dict]:
    with open(SKILLS_PATH, encoding="utf-8") as f:
        return json.load(f)


def skill_index() -> Dict[str, dict]:
    return {s["id"]: s for s in load_skills()}


def resolve_id(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    key = name.strip().lower()
    if key in skill_index():
        return key
    if key in ALIASES:
        return ALIASES[key]
    for skill in load_skills():
        if skill["name"].lower() == key:
            return skill["id"]
    return ALIASES.get(key.replace("_", " "))


def required_skills_for_goal(goal: str, target_role: str = "") -> List[str]:
    blob = f"{target_role} {goal}".strip().lower()
    for key, skills in GOAL_SKILLS.items():
        if key in blob:
            return list(skills)
    if "analyst" in blob:
        return list(GOAL_SKILLS["data analyst"])
    if "front" in blob:
        return list(GOAL_SKILLS["frontend"])
    if "back" in blob:
        return list(GOAL_SKILLS["backend"])
    if "ml" in blob or "machine" in blob or "ai" in blob:
        return list(GOAL_SKILLS["ml engineer"])
    return []


def _prereq_map() -> Dict[str, List[str]]:
    return {s["id"]: list(s.get("prerequisites") or []) for s in load_skills()}


def ancestors(skill_id: str, extra_prereqs: Optional[Dict[str, List[str]]] = None) -> List[str]:
    prereqs = {**_prereq_map(), **(extra_prereqs or {})}
    seen = []
    stack = list(prereqs.get(skill_id, []))
    visiting = set()
    while stack:
        current = stack.pop()
        if current in visiting or current in seen:
            continue
        visiting.add(current)
        seen.append(current)
        stack.extend(prereqs.get(current, []))
    return seen


def ordered_skills(skill_ids: Iterable[str], extra_prereqs: Optional[Dict[str, List[str]]] = None) -> List[str]:
    """Topological order including prerequisites of the requested skills."""
    extra = extra_prereqs or {}
    needed = set()
    for sid in skill_ids:
        if not sid:
            continue
        needed.add(sid)
        needed.update(ancestors(sid, extra))
    prereqs = {**_prereq_map(), **extra}
    incoming = defaultdict(int)
    edges = defaultdict(list)
    for sid in needed:
        for p in prereqs.get(sid, []):
            if p in needed:
                edges[p].append(sid)
                incoming[sid] += 1
        incoming.setdefault(sid, incoming.get(sid, 0))
    queue = deque(sorted([s for s in needed if incoming[s] == 0]))
    ordered = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for nxt in sorted(edges[node]):
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                queue.append(nxt)
    for sid in needed:
        if sid not in ordered:
            ordered.append(sid)
    return ordered


def graph_payload(
    learner_skills: Optional[list] = None,
    focus_ids: Optional[List[str]] = None,
    extra_defs: Optional[Dict[str, dict]] = None,
) -> dict:
    proficiency = {}
    required_override = {}
    for skill in learner_skills or []:
        if not isinstance(skill, dict):
            continue
        sid = skill.get("skill_id") or resolve_id(skill.get("name"))
        if sid:
            proficiency[sid] = int(skill.get("proficiency") or 0)
            if skill.get("required") is not None:
                required_override[sid] = int(skill["required"])
    nodes = []
    edges = []
    extras = extra_defs or {}
    index = {**skill_index(), **extras}
    extra_prereqs = {sid: list(meta.get("prerequisites") or []) for sid, meta in extras.items()}
    include = set(focus_ids or index.keys())
    for extra in list(include):
        include.update(ancestors(extra, extra_prereqs))
        include.add(extra)
    for sid in include:
        meta = index.get(sid)
        if not meta:
            continue
        nodes.append(
            {
                "id": sid,
                "name": meta.get("name", sid),
                "proficiency": proficiency.get(sid, 0),
                "required": required_override.get(sid, meta.get("required", 70)),
                "importance": meta.get("importance", 0.5),
            }
        )
        for p in meta.get("prerequisites") or []:
            if p in include:
                edges.append({"source": p, "target": sid, "relation": "PREREQUISITE_OF"})
    return {"nodes": nodes, "edges": edges}
