from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.groq_client import get_groq_response
from app.models import Learner, LearnerSkill, LearnerTopicMastery, Skill, SkillTopic
from app.services import graph_service
from app.services.goal_service import slugify
from app.services.learner_service import merge_skills, normalize_skill

from fastapi import HTTPException


CANONICAL = {
    "data-analyst": ("Data Analyst", "data", graph_service.GOAL_SKILLS["data analyst"]),
    "data-scientist": ("Data Scientist", "data", graph_service.GOAL_SKILLS["data scientist"]),
    "ml-engineer": ("ML Engineer", "ml", graph_service.GOAL_SKILLS["ml engineer"]),
    "machine-learning": ("Machine Learning", "ml", graph_service.GOAL_SKILLS["machine learning"]),
    "frontend": ("Frontend", "web", graph_service.GOAL_SKILLS["frontend"]),
    "backend": ("Backend", "web", graph_service.GOAL_SKILLS["backend"]),
    "full-stack": ("Full Stack", "web", graph_service.GOAL_SKILLS["full stack"]),
    "ai": ("AI", "ml", graph_service.GOAL_SKILLS["ai"]),
}

NAME_TO_CANONICAL = {
    "data analyst": "data-analyst",
    "become a data analyst": "data-analyst",
    "data scientist": "data-scientist",
    "ml engineer": "ml-engineer",
    "machine learning": "machine-learning",
    "frontend developer": "frontend",
    "frontend": "frontend",
    "backend developer": "backend",
    "backend": "backend",
    "full stack": "full-stack",
    "ai": "ai",
    "python": "python",
    "dbms": "dbms",
    "sql": "dbms",
    "database": "dbms",
    "databases": "dbms",
    "guitar": "guitar",
}

MVP_TAXONOMIES = {
    "python": (
        "Python",
        "tech",
        [
            ("syntax", "Python syntax", []),
            ("functions", "Functions", ["syntax"]),
            ("data-structures", "Lists, dicts, and sets", ["syntax"]),
            ("oop", "Object-oriented Python", ["functions"]),
            ("stdlib", "Standard library", ["functions"]),
            ("files-exceptions", "Files and exceptions", ["syntax"]),
        ],
    ),
    "dbms": (
        "DBMS",
        "data",
        [
            ("relational-model", "Relational model", []),
            ("sql-select", "SQL queries", ["relational-model"]),
            ("joins", "Joins", ["sql-select"]),
            ("normalization", "Normalization", ["relational-model"]),
            ("indexes", "Indexes", ["sql-select"]),
            ("transactions", "Transactions", ["sql-select"]),
        ],
    ),
    "guitar": (
        "Guitar",
        "music",
        [
            ("open-chords", "Open chords", []),
            ("strumming", "Strumming", ["open-chords"]),
            ("rhythm", "Rhythm", ["strumming"]),
            ("chord-transitions", "Chord transitions", ["open-chords"]),
            ("technique", "Right-hand technique", ["strumming"]),
            ("fretboard", "Fretboard knowledge", ["open-chords"]),
            ("scales", "Scales", ["fretboard"]),
            ("repertoire", "Song repertoire", ["chord-transitions", "rhythm"]),
        ],
    ),
}


MVP_MAJORS = {
    "python": [
        ("foundations", "Foundations", ["syntax", "functions", "data-structures"]),
        ("intermediate", "Intermediate Python", ["oop", "stdlib", "files-exceptions"]),
    ],
    "dbms": [
        ("modeling", "Data modeling", ["relational-model", "normalization"]),
        ("querying", "Querying", ["sql-select", "joins", "indexes"]),
        ("systems", "Database systems", ["transactions"]),
    ],
    "guitar": [
        ("foundations", "Foundations", ["open-chords", "strumming", "chord-transitions"]),
        ("technique", "Technique", ["rhythm", "technique"]),
        ("fretboard", "Fretboard", ["fretboard", "scales"]),
        ("repertoire", "Repertoire", ["repertoire"]),
    ],
}

CANONICAL_MAJORS = {
    "data-analyst": [
        ("foundations", "Foundations", ["python", "sql", "excel"]),
        ("analysis", "Analysis", ["statistics", "pandas", "data-analysis"]),
        ("communication", "Communication", ["data-visualization"]),
    ],
    "data-scientist": [
        ("foundations", "Foundations", ["python", "numpy", "pandas", "sql"]),
        ("stats", "Statistics", ["statistics", "probability"]),
        ("ml", "Machine learning", ["machine-learning", "data-visualization"]),
    ],
    "ml-engineer": [
        ("foundations", "Foundations", ["python", "numpy", "pandas"]),
        ("math", "Math", ["statistics", "probability", "linear-algebra"]),
        ("ml", "ML systems", ["machine-learning", "deep-learning", "mlops"]),
    ],
    "machine-learning": [
        ("foundations", "Foundations", ["python", "numpy", "pandas"]),
        ("core", "Core ML", ["statistics", "probability", "machine-learning"]),
    ],
    "frontend": [
        ("foundations", "Web foundations", ["html", "css", "javascript", "git"]),
        ("frameworks", "Frameworks", ["react", "typescript", "accessibility"]),
    ],
    "backend": [
        ("foundations", "Foundations", ["python", "git", "sql"]),
        ("apis", "APIs and services", ["fastapi", "postgresql", "docker"]),
    ],
}


class TopicIn(BaseModel):
    id: str = ""
    name: str
    parent_id: Optional[str] = None
    prerequisites: List[str] = Field(default_factory=list)
    required: int = 70

    @field_validator("name")
    @classmethod
    def name_ok(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("topic name required")
        return v.strip()


class TaxonomyIn(BaseModel):
    skill_id: str = ""
    name: str
    description: str = ""
    domain: str = "general"
    topics: List[TopicIn]

    @field_validator("name")
    @classmethod
    def name_ok(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("skill name required")
        return v.strip()

    @field_validator("topics")
    @classmethod
    def topics_ok(cls, v: List[TopicIn]) -> List[TopicIn]:
        if len(v) < 3:
            raise ValueError("need at least 3 topics")
        return v[:12]


def topic_key(skill_id: str, slug: str) -> str:
    slug = slugify(slug)
    if slug.startswith(f"{skill_id}--"):
        return slug
    return f"{skill_id}--{slug}"


def catalog_keys_for_topic(topic: SkillTopic) -> List[str]:
    keys = [topic.id, topic.slug, topic.skill_id]
    if "--" in topic.id:
        keys.append(topic.id.split("--", 1)[-1])
    return [k for k in keys if k]


def mastery_status(proficiency: int, required: int, evidence_count: int) -> str:
    if evidence_count <= 0 and proficiency <= 0:
        return "not_assessed"
    if proficiency >= required - 5:
        return "proficient"
    if proficiency < required * 0.5:
        return "weak"
    return "learning"


def seed_catalog_skills(db: Session) -> None:
    index = graph_service.skill_index()
    for sid, (name, domain, topic_ids) in CANONICAL.items():
        skill = db.get(Skill, sid)
        if not skill:
            skill = Skill(id=sid, name=name, description=f"Canonical {name} skill", domain=domain, source="catalog")
            db.add(skill)
            db.flush()
        existing = {t.id for t in db.query(SkillTopic).filter(SkillTopic.skill_id == sid).all()}
        for raw_id in topic_ids:
            tid = topic_key(sid, raw_id)
            if tid in existing:
                continue
            meta = index.get(raw_id) or {}
            prereqs = [topic_key(sid, p) for p in (meta.get("prerequisites") or []) if p in topic_ids]
            db.add(
                SkillTopic(
                    id=tid,
                    skill_id=sid,
                    parent_id="",
                    name=meta.get("name", raw_id),
                    slug=raw_id,
                    prerequisites=prereqs,
                    required=int(meta.get("required") or 70),
                )
            )
    for sid, (name, domain, rows) in MVP_TAXONOMIES.items():
        skill = db.get(Skill, sid)
        if not skill:
            skill = Skill(id=sid, name=name, description=f"Canonical {name} skill", domain=domain, source="catalog")
            db.add(skill)
            db.flush()
        else:
            skill.name = name
            skill.domain = domain
        existing = {t.id for t in db.query(SkillTopic).filter(SkillTopic.skill_id == sid).all()}
        for i, (slug, tname, prereqs) in enumerate(rows):
            tid = topic_key(sid, slug)
            mapped_prereqs = [topic_key(sid, p) for p in prereqs]
            if tid in existing:
                topic = db.get(SkillTopic, tid)
                if topic:
                    topic.name = tname
                    topic.prerequisites = mapped_prereqs
                    topic.sort_order = i
                continue
            db.add(
                SkillTopic(
                    id=tid,
                    skill_id=sid,
                    parent_id="",
                    name=tname,
                    slug=slug,
                    prerequisites=mapped_prereqs,
                    required=70,
                    sort_order=i,
                )
            )
    for raw in graph_service.load_skills():
        sid = raw["id"]
        if db.get(Skill, sid):
            continue
        db.add(Skill(id=sid, name=raw["name"], description="", domain="tech", source="catalog"))
        db.flush()
        db.add(
            SkillTopic(
                id=topic_key(sid, sid),
                skill_id=sid,
                parent_id="",
                name=raw["name"],
                slug=sid,
                prerequisites=[],
                required=int(raw.get("required") or 70),
            )
        )
    for sid, majors in {**CANONICAL_MAJORS, **MVP_MAJORS}.items():
        if db.get(Skill, sid):
            _attach_majors(db, sid, majors)
    db.commit()


def is_major_topic(topic: SkillTopic) -> bool:
    return (topic.slug or "").startswith("major-") or (topic.id or "").find("--major-") >= 0


def leaf_topics_for_skill(db: Session, skill_id: str) -> List[SkillTopic]:
    return [t for t in topics_for_skill(db, skill_id) if not is_major_topic(t)]


def _attach_majors(db: Session, skill_id: str, majors: list) -> None:
    existing = {t.slug: t for t in db.query(SkillTopic).filter(SkillTopic.skill_id == skill_id).all()}
    for i, (slug, name, child_slugs) in enumerate(majors):
        major_slug = f"major-{slug}"
        mid = topic_key(skill_id, major_slug)
        major = db.get(SkillTopic, mid)
        if not major:
            major = SkillTopic(
                id=mid,
                skill_id=skill_id,
                parent_id="",
                name=name,
                slug=major_slug,
                prerequisites=[],
                required=70,
                sort_order=-20 + i,
            )
            db.add(major)
            db.flush()
        else:
            major.name = name
            major.slug = major_slug
            major.sort_order = -20 + i
        for child_slug in child_slugs:
            child = existing.get(child_slug) or db.get(SkillTopic, topic_key(skill_id, child_slug))
            if child and not is_major_topic(child):
                child.parent_id = mid


def serialize_skill(skill: Skill) -> dict:
    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description or "",
        "domain": skill.domain,
        "taxonomy_version": skill.taxonomy_version,
        "source": skill.source,
    }


def serialize_topic(topic: SkillTopic, mastery: Optional[LearnerTopicMastery] = None) -> dict:
    required = int(topic.required or 70)
    proficiency = int(mastery.proficiency) if mastery else 0
    confidence = int(mastery.confidence) if mastery else 0
    evidence = int(mastery.evidence_count) if mastery else 0
    return {
        "id": topic.id,
        "skill_id": topic.skill_id,
        "parent_id": topic.parent_id or "",
        "name": topic.name,
        "slug": topic.slug or topic.id,
        "prerequisites": topic.prerequisites or [],
        "required": required,
        "proficiency": proficiency,
        "confidence": confidence,
        "status": mastery_status(proficiency, required, evidence) if mastery else "not_assessed",
        "evidence_count": evidence,
    }


def topics_for_skill(db: Session, skill_id: str) -> List[SkillTopic]:
    return db.query(SkillTopic).filter(SkillTopic.skill_id == skill_id).order_by(SkillTopic.sort_order.asc(), SkillTopic.name.asc()).all()


def _match_existing(db: Session, raw: str) -> Optional[Skill]:
    key = (raw or "").strip().lower()
    if not key:
        return None
    slug = slugify(key)
    mapped = NAME_TO_CANONICAL.get(key) or NAME_TO_CANONICAL.get(slug)
    if mapped:
        found = db.get(Skill, mapped)
        if found:
            return found
    skill = db.get(Skill, slug)
    if skill:
        return skill
    by_name = db.query(Skill).filter(Skill.name.ilike(key)).first()
    if by_name:
        return by_name
    for token, canon_id in NAME_TO_CANONICAL.items():
        if token in ("ai",) and token != key:
            continue
        if token in key:
            return db.get(Skill, canon_id)
    resolved = graph_service.resolve_id(key)
    if resolved:
        return db.get(Skill, resolved)
    return None


def _persist_taxonomy(db: Session, tax: TaxonomyIn) -> Skill:
    skill_id = slugify(tax.skill_id or tax.name)
    skill = db.get(Skill, skill_id)
    if not skill:
        skill = Skill(
            id=skill_id,
            name=tax.name,
            description=tax.description or "",
            domain=tax.domain or "general",
            source="llm",
            taxonomy_version=1,
        )
        db.add(skill)
        db.flush()
    slug_map = {}
    for topic in tax.topics:
        local = slugify(topic.id or topic.name)
        slug_map[local] = topic_key(skill_id, local)
        if topic.id:
            slug_map[slugify(topic.id)] = topic_key(skill_id, local)
    for topic in tax.topics:
        local = slugify(topic.id or topic.name)
        tid = topic_key(skill_id, local)
        parent = ""
        if topic.parent_id:
            parent = slug_map.get(slugify(topic.parent_id), "")
        prereqs = [slug_map[slugify(p)] for p in topic.prerequisites if slugify(p) in slug_map]
        existing = db.get(SkillTopic, tid)
        if existing:
            existing.name = topic.name
            existing.prerequisites = prereqs
            existing.parent_id = parent
            existing.required = int(topic.required or 70)
            continue
        db.add(
            SkillTopic(
                id=tid,
                skill_id=skill_id,
                parent_id=parent,
                name=topic.name,
                slug=local,
                prerequisites=prereqs,
                required=int(topic.required or 70),
            )
        )
    db.flush()
    return skill


def generate_taxonomy(name: str) -> TaxonomyIn:
    prompt = f"""
Create a skill taxonomy as JSON for this skill: {name}

{{
  "skill_id": "kebab-case",
  "name": "Human name",
  "description": "one sentence",
  "domain": "music|language|sport|design|tech|general",
  "topics": [
    {{"id": "kebab-id", "name": "Topic", "parent_id": null, "prerequisites": [], "required": 70}}
  ]
}}

6 to 10 topics specific to THIS skill. Do not use programming/Python/SQL/JavaScript unless the skill is software.
"""
    try:
        data = get_groq_response(prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not generate a skill taxonomy: {exc}") from exc
    try:
        return TaxonomyIn.model_validate(data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Invalid skill taxonomy from the model: {exc}") from exc


def resolve_skill(db: Session, name: str) -> Skill:
    seed_catalog_skills(db)
    existing = _match_existing(db, name)
    if existing and topics_for_skill(db, existing.id):
        return existing
    tax = generate_taxonomy(name)
    return _persist_taxonomy(db, tax)


def sync_json_skills(learner: Learner, db: Session, skill_id: str) -> None:
    topics = topics_for_skill(db, skill_id)
    mastery = {
        m.topic_id: m
        for m in db.query(LearnerTopicMastery).filter(LearnerTopicMastery.learner_id == learner.id).all()
    }
    incoming = []
    subskills = []
    for topic in topics:
        m = mastery.get(topic.id)
        incoming.append(
            normalize_skill(
                {
                    "name": topic.name,
                    "skill_id": topic.id,
                    "proficiency": int(m.proficiency) if m else 0,
                    "required": topic.required,
                    "source": "goal",
                }
            )
        )
        subskills.append(
            {
                "id": topic.id,
                "name": topic.name,
                "prerequisites": topic.prerequisites or [],
                "required": topic.required,
            }
        )
    learner.skills = merge_skills(learner.skills or [], [s for s in incoming if s])
    learner.goal_subskills = subskills
    skill = db.get(Skill, skill_id)
    if skill and not learner.goal:
        learner.goal = f"Learn {skill.name}"


def ensure_learner_skill(db: Session, learner: Learner, skill_id: str) -> LearnerSkill:
    row = (
        db.query(LearnerSkill)
        .filter(LearnerSkill.learner_id == learner.id, LearnerSkill.skill_id == skill_id)
        .first()
    )
    if not row:
        row = LearnerSkill(learner_id=learner.id, skill_id=skill_id, overall_proficiency=0, confidence=0, status="not_assessed")
        db.add(row)
        db.flush()
    for topic in topics_for_skill(db, skill_id):
        existing = (
            db.query(LearnerTopicMastery)
            .filter(LearnerTopicMastery.learner_id == learner.id, LearnerTopicMastery.topic_id == topic.id)
            .first()
        )
        if not existing:
            db.add(
                LearnerTopicMastery(
                    learner_id=learner.id,
                    topic_id=topic.id,
                    proficiency=0,
                    confidence=0,
                    status="not_assessed",
                    evidence_count=0,
                )
            )
    learner.active_skill_id = skill_id
    sync_json_skills(learner, db, skill_id)
    db.flush()
    return row


def resolve_for_learner(db: Session, learner: Learner, name: str) -> dict:
    skill = resolve_skill(db, name)
    row = ensure_learner_skill(db, learner, skill.id)
    db.commit()
    db.refresh(learner)
    mastery = {
        m.topic_id: m
        for m in db.query(LearnerTopicMastery).filter(LearnerTopicMastery.learner_id == learner.id).all()
    }
    topics = [serialize_topic(t, mastery.get(t.id)) for t in topics_for_skill(db, skill.id)]
    return {
        "skill": serialize_skill(skill),
        "topics": topics,
        "learner_skill": {
            "skill_id": row.skill_id,
            "overall_proficiency": row.overall_proficiency,
            "confidence": row.confidence,
            "status": row.status,
        },
        "learner": __import__("app.services.learner_service", fromlist=["learner_to_dict"]).learner_to_dict(learner),
    }


def active_skill_id(learner: Learner, db: Session) -> str:
    sid = getattr(learner, "active_skill_id", "") or ""
    if sid and db.get(Skill, sid):
        return sid
    row = db.query(LearnerSkill).filter(LearnerSkill.learner_id == learner.id).first()
    if row:
        return row.skill_id
    return ""


def list_learner_skills(db: Session, learner: Learner) -> list:
    rows = db.query(LearnerSkill).filter(LearnerSkill.learner_id == learner.id).all()
    out = []
    for row in rows:
        skill = db.get(Skill, row.skill_id)
        if not skill:
            continue
        out.append(
            {
                **serialize_skill(skill),
                "overall_proficiency": row.overall_proficiency,
                "confidence": row.confidence,
                "status": row.status,
                "active": row.skill_id == (learner.active_skill_id or ""),
            }
        )
    return out


def set_active_skill(db: Session, learner: Learner, skill_id: str) -> dict:
    row = (
        db.query(LearnerSkill)
        .filter(LearnerSkill.learner_id == learner.id, LearnerSkill.skill_id == skill_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Skill is not on this learner yet. Resolve it first.")
    learner.active_skill_id = skill_id
    sync_json_skills(learner, db, skill_id)
    db.commit()
    return {"active_skill_id": skill_id, "learner": __import__("app.services.learner_service", fromlist=["learner_to_dict"]).learner_to_dict(learner)}


def get_mastery(db: Session, learner_id: str, topic_id: str) -> Optional[LearnerTopicMastery]:
    return (
        db.query(LearnerTopicMastery)
        .filter(LearnerTopicMastery.learner_id == learner_id, LearnerTopicMastery.topic_id == topic_id)
        .first()
    )


def apply_topic_score(db: Session, learner: Learner, topic_id: str, quiz: int) -> LearnerTopicMastery:
    from app.services.learner_service import blend_proficiency

    topic = db.get(SkillTopic, topic_id)
    row = get_mastery(db, learner.id, topic_id)
    if not row:
        row = LearnerTopicMastery(learner_id=learner.id, topic_id=topic_id)
        db.add(row)
        db.flush()
    row.proficiency = blend_proficiency(int(row.proficiency or 0), quiz)
    row.evidence_count = int(row.evidence_count or 0) + 1
    row.confidence = min(100, row.evidence_count * 22)
    required = int(topic.required) if topic else 70
    row.status = mastery_status(row.proficiency, required, row.evidence_count)
    return row


def rollup_skill(db: Session, learner: Learner, skill_id: str) -> None:
    topics = leaf_topics_for_skill(db, skill_id)
    if not topics:
        return
    scores = []
    confs = []
    evidence = 0
    for topic in topics:
        m = get_mastery(db, learner.id, topic.id)
        scores.append(int(m.proficiency) if m else 0)
        confs.append(int(m.confidence) if m else 0)
        evidence += int(m.evidence_count) if m else 0
    row = (
        db.query(LearnerSkill)
        .filter(LearnerSkill.learner_id == learner.id, LearnerSkill.skill_id == skill_id)
        .first()
    )
    if not row:
        return
    row.overall_proficiency = int(sum(scores) / len(scores))
    row.confidence = int(sum(confs) / len(confs)) if confs else 0
    required_avg = int(sum(t.required for t in topics) / len(topics))
    row.status = mastery_status(row.overall_proficiency, required_avg, evidence)
    sync_json_skills(learner, db, skill_id)


def bump_topic(db: Session, learner: Learner, topic_id: str, delta: int) -> None:
    topic = db.get(SkillTopic, topic_id)
    row = get_mastery(db, learner.id, topic_id)
    if not row:
        row = LearnerTopicMastery(learner_id=learner.id, topic_id=topic_id)
        db.add(row)
        db.flush()
    row.proficiency = int(max(0, min(92, (row.proficiency or 0) + delta)))
    row.evidence_count = int(row.evidence_count or 0) + 1
    row.confidence = min(100, row.evidence_count * 18)
    required = int(topic.required) if topic else 70
    row.status = mastery_status(row.proficiency, required, row.evidence_count)
    if topic:
        rollup_skill(db, learner, topic.skill_id)


def topic_graph(db: Session, learner: Learner, skill_id: str) -> dict:
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    ensure_learner_skill(db, learner, skill_id)
    topics = topics_for_skill(db, skill_id)
    mastery = {
        m.topic_id: m
        for m in db.query(LearnerTopicMastery).filter(LearnerTopicMastery.learner_id == learner.id).all()
    }
    enrolled = (
        db.query(LearnerSkill)
        .filter(LearnerSkill.learner_id == learner.id, LearnerSkill.skill_id == skill_id)
        .first()
    )
    nodes = [
        {
            "id": skill.id,
            "name": skill.name,
            "kind": "skill",
            "proficiency": enrolled.overall_proficiency if enrolled else 0,
            "confidence": enrolled.confidence if enrolled else 0,
            "required": 70,
            "status": enrolled.status if enrolled else "not_assessed",
            "importance": 1,
        }
    ]
    edges = []
    for topic in topics:
        row = serialize_topic(topic, mastery.get(topic.id))
        kind = "major" if is_major_topic(topic) else "topic"
        nodes.append(
            {
                "id": topic.id,
                "name": topic.name,
                "kind": kind,
                "parent_id": topic.parent_id or skill.id,
                "proficiency": row["proficiency"],
                "confidence": row["confidence"],
                "required": row["required"],
                "status": row["status"],
                "importance": 0.9 if kind == "major" else 0.7,
            }
        )
        parent = topic.parent_id or skill.id
        edges.append({"source": parent, "target": topic.id, "relation": "PARENT_OF"})
        for p in topic.prerequisites or []:
            edges.append({"source": p, "target": topic.id, "relation": "PREREQUISITE_OF"})
    return {"skill": serialize_skill(skill), "nodes": nodes, "edges": edges}


def weak_topics(db: Session, learner: Learner, skill_id: str, skip_ids=None, focus_ids=None) -> List[SkillTopic]:
    skip = set(skip_ids or [])
    focus = set(focus_ids or [])
    topics = topics_for_skill(db, skill_id)
    by_id = {t.id: t for t in topics}
    extra = {t.id: list(t.prerequisites or []) for t in topics}
    ordered_ids = graph_service.ordered_skills([t.id for t in topics], extra_prereqs=extra)
    out = []
    for tid in ordered_ids:
        topic = by_id.get(tid)
        if not topic or tid in skip or is_major_topic(topic):
            continue
        m = get_mastery(db, learner.id, tid)
        status = m.status if m else "not_assessed"
        if focus and tid not in focus:
            continue
        if status == "proficient" and tid not in focus:
            continue
        out.append(topic)
    return out
