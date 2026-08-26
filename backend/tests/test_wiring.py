from fastapi.testclient import TestClient
from unittest.mock import patch
import os
import sys
import tempfile

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["GROQ_API_KEY"] = "dummy_key"
os.environ["ACADBRIDGE_SKIP_URL_FETCH"] = "1"
os.environ["TAVILY_API_KEY"] = ""
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.main import app
from app.db import init_db

init_db()
client = TestClient(app)

MOCK_SEMESTER_RESPONSE = {
    "semester_detected": "Semester 5",
    "theory_subjects": [
        {
            "name": "Subject A",
            "topics": [
                {
                    "name": "Topic 1",
                    "industry_relevance": "High",
                    "industry_skill": "Python",
                    "industry_tools": ["NumPy"],
                    "extra_learning": ["Pandas"],
                }
            ],
        }
    ],
    "lab_subjects": [],
    "industry_skills": [{"name": "Skill A", "category": "Core", "status": "Learning"}],
    "industry_relevance": "High",
    "semester_readiness_score": 85,
    "summary_card_data": {
        "total_subjects": 1,
        "total_topics": 1,
        "total_skills": 1,
        "top_industry_skills": ["Python"],
    },
}

MOCK_RESUME_RESPONSE = {
    "ats_optimized_resume_text": "Resume content...",
    "ats_match_percentage": 90,
    "missing_keywords": ["python"],
}

MOCK_ROLE_FIT_RESPONSE = {
    "role_fit_percentage": 90,
    "strengths": ["Skill A"],
    "missing_skills": ["Skill B"],
    "in_progress_skills": [],
    "learning_plan": [{"skill": "Skill B", "topics": ["Intro"]}],
    "recommended_jobs": [
        {"title": "Junior Backend Engineer", "seniority": "junior", "match_percent": 80, "why": "Python match", "missing_skills": ["Skill B"]}
    ],
}

MOCK_ROADMAP_RESPONSE = {
    "feasible": True,
    "recommendation": "This plan fits your timeline.",
    "roadmap": [
        {
            "week": 1,
            "focus": "Basics",
            "topics": ["Skill A"],
            "practice": "Build X",
            "estimated_hours": 8,
        }
    ],
}

MOCK_PATH_ITEMS = {
    "items": [
        {
            "catalog_id": "data-sql-sqlbolt",
            "why": "SQL is a core gap for analysts.",
            "milestone_title": "",
            "prereq_ids": [],
        },
        {
            "catalog_id": "project-sql-analysis",
            "why": "Apply SQL on a real dataset.",
            "milestone_title": "Milestone 1: SQL project",
            "prereq_ids": ["data-sql-sqlbolt"],
        },
        {
            "catalog_id": "assess-sql-leetcode",
            "why": "Checkpoint your SQL fluency.",
            "milestone_title": "",
            "prereq_ids": ["data-sql-sqlbolt"],
        },
    ]
}


@patch("app.services.semester_service.get_groq_response", return_value=MOCK_SEMESTER_RESPONSE)
def test_semester_analyze(mock_groq):
    response = client.post(
        "/api/semester/analyze",
        data={"syllabus_text": "Sample syllabus", "manual_semester": "Semester 5"},
    )
    assert response.status_code == 200
    assert response.json()["semester_detected"] == "Semester 5"


@patch("app.services.resume_service.get_groq_response", return_value=MOCK_RESUME_RESPONSE)
def test_resume_generate(mock_groq):
    response = client.post(
        "/api/resume/generate",
        json={"target_role": "Backend Dev", "tools": ["Python"], "achievements": ["Built API"]},
    )
    assert response.status_code == 200
    assert response.json()["ats_match_percentage"] == 90


@patch("app.services.role_fit_service.get_groq_response", return_value=MOCK_ROLE_FIT_RESPONSE)
def test_role_fit_analyze(mock_groq):
    response = client.post(
        "/api/role-fit/analyze",
        json={"target_role": "Backend Dev", "current_skills": ["Python"]},
    )
    assert response.status_code == 200
    assert response.json()["role_fit_percentage"] == 90


@patch("app.services.roadmap_service.get_groq_response", return_value=MOCK_ROADMAP_RESPONSE)
def test_roadmap_generate(mock_groq):
    response = client.post(
        "/api/roadmap/generate",
        json={"target_role": "Backend Dev", "experience_level": "Beginner"},
    )
    assert response.status_code == 200
    assert len(response.json()["roadmap"]) == 1


def test_login_and_profile_roundtrip():
    created = client.post("/api/learner/login", json={"email": "ada@university.edu", "name": "Ada"})
    assert created.status_code == 200
    learner_id = created.json()["id"]
    fetched = client.get(f"/api/learner/{learner_id}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "ada@university.edu"

    updated = client.put(
        f"/api/learner/{learner_id}",
        json={"goal": "Become a data analyst", "interests": ["SQL"], "hours_per_week": 8},
    )
    assert updated.status_code == 200
    assert updated.json()["goal"] == "Become a data analyst"


def test_catalog_lists_resources():
    response = client.get("/api/catalog/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 40
    assert any(item["id"] == "data-sql-sqlbolt" for item in body["items"])


def test_path_generate_complete_and_adapt():
    learner = client.post("/api/learner/login", json={"email": "path@university.edu", "name": "Path"}).json()
    client.put(
        f"/api/learner/{learner['id']}",
        json={"goal": "Become a data analyst", "target_role": "Data Analyst", "budget": "free"},
    )
    path = client.post("/api/path/generate", json={"learner_id": learner["id"]})
    assert path.status_code == 200
    items = path.json()["items"]
    assert len(items) >= 2
    assert "why" in items[0]
    assert any(i.get("week") for i in items)

    patched = client.patch(f"/api/path/items/{items[0]['id']}", json={"status": "done"})
    assert patched.status_code == 200
    done = [i for i in patched.json()["items"] if i["status"] == "done"]
    assert len(done) >= 1

    dashboard = client.get(f"/api/dashboard/{learner['id']}")
    assert dashboard.status_code == 200
    assert dashboard.json()["items_done"] >= 1
    assert "skill_bars" in dashboard.json()

    adapted = client.post("/api/path/adapt", json={"learner_id": learner["id"]})
    assert adapted.status_code == 200
    assert adapted.json()["items"]


def test_skill_graph_and_gaps():
    from app.services.graph_service import ordered_skills, required_skills_for_goal

    req = required_skills_for_goal("Become an ML Engineer", "ML Engineer")
    ordered = ordered_skills(req)
    assert ordered.index("python") < ordered.index("machine-learning")
    assert ordered.index("probability") < ordered.index("statistics")

    learner = client.post("/api/learner/login", json={"email": "gap@university.edu"}).json()
    client.put(f"/api/learner/{learner['id']}", json={"goal": "ML Engineer", "target_role": "ML Engineer"})
    gaps = client.get(f"/api/skills/gaps/{learner['id']}")
    assert gaps.status_code == 200
    rows = gaps.json()["gaps"]
    assert any("python" in r["skill_id"] for r in rows)
    graph = client.get(f"/api/skills/graph/{learner['id']}")
    assert graph.status_code == 200
    assert len(graph.json()["nodes"]) >= 5
    assert graph.json()["edges"]


def test_ranking_prefers_free_handson():
    from app.services.catalog_service import get_by_id, rank_resource

    sql = get_by_id("data-sql-sqlbolt")
    assert sql["cost"] == "free"
    score = rank_resource(
        sql, skill_id="sql", proficiency=20, preference="hands-on", budget="free", hours_per_day=1
    )
    assert score > 3


def test_unmatched_goal_not_analyst():
    from app.services.graph_service import required_skills_for_goal

    ids = required_skills_for_goal("learn guitar in 5 months, 1 hour each day")
    assert ids == []
    assert "python" not in ids
    assert "sql" not in ids
    assert "javascript" not in ids

    learner = client.post("/api/learner/login", json={"email": "guitar-gap@university.edu"}).json()
    updated = client.put(
        f"/api/learner/{learner['id']}",
        json={"goal": "learn guitar in 5 months, 1 hour each day"},
    )
    assert updated.status_code == 200
    skill_ids = [s.get("skill_id") for s in updated.json().get("skills") or []]
    assert "python" not in skill_ids
    assert "sql" not in skill_ids
    assert "excel" not in skill_ids


GUITAR_DECOMPOSE = {
    "goal": "learn guitar",
    "domain": "music",
    "primary_skill": "guitar",
    "duration_months": 5,
    "daily_minutes": 60,
    "current_level": "beginner",
    "subskills": [
        {"id": "open-chords", "name": "Open chords", "prerequisites": [], "required": 70},
        {"id": "strumming", "name": "Strumming", "prerequisites": ["open-chords"], "required": 70},
        {"id": "rhythm", "name": "Rhythm", "prerequisites": ["strumming"], "required": 65},
        {"id": "fingerpicking", "name": "Fingerpicking", "prerequisites": ["open-chords"], "required": 60},
        {"id": "barre-chords", "name": "Barre chords", "prerequisites": ["open-chords"], "required": 75},
        {"id": "repertoire", "name": "Song repertoire", "prerequisites": ["strumming"], "required": 70},
    ],
}

GUITAR_QUESTION = {
    "skill_id": "open-chords",
    "skill": "Open chords",
    "difficulty": "easy",
    "question": "Which of these is a standard open guitar chord?",
    "options": ["E major", "H diminished 13", "TCP handshake", "LEFT JOIN"],
    "correct": "E major",
}


def _groq_for_guitar(prompt: str, **_kwargs):
    lowered = prompt.lower()
    if "month-by-month" in lowered or "learning plan" in lowered or "json resources for these topics" in lowered:
        return {
            "resources": [
                {
                    "month": 1,
                    "topic_id": "guitar--open-chords",
                    "skill_id": "open-chords",
                    "title": "JustinGuitar Beginner Course",
                    "url": "https://www.justinguitar.com/guitar-lessons/beginner-guitar-course-grade-1",
                    "type": "course",
                    "skill_name": "Open chords",
                    "why": "Foundational open chords for a 5-month guitar plan.",
                },
                {
                    "month": 2,
                    "topic_id": "strumming",
                    "skill_id": "strumming",
                    "title": "Strumming patterns practice",
                    "url": "https://www.justinguitar.com/",
                    "type": "practice",
                    "skill_name": "Strumming",
                    "why": "Build rhythm after open chords.",
                },
            ]
        }
    if "parse this learning goal" in lowered or "decompose" in lowered:
        return GUITAR_DECOMPOSE
    return dict(GUITAR_QUESTION)


@patch("app.services.assessment_service.get_groq_response", side_effect=_groq_for_guitar)
@patch("app.services.goal_service.get_groq_response", side_effect=_groq_for_guitar)
def test_guitar_assessment_is_not_programming(mock_goal, mock_quiz):
    learner = client.post("/api/learner/login", json={"email": "guitar@university.edu"}).json()
    client.put(
        f"/api/learner/{learner['id']}",
        json={"goal": "learn guitar in 5 months, 1 hour each day"},
    )
    quiz = client.post("/api/assessment/generate", json={"learner_id": learner["id"], "skill_id": "guitar"})
    assert quiz.status_code == 200, quiz.text
    blob = str(quiz.json()).lower()
    assert "javascript" not in blob
    assert "python" not in blob
    item = quiz.json()["current_item"] or quiz.json()["items"][0]
    assert "chord" in (item.get("skill_name") or item.get("skill_id") or "").lower() or "chord" in item["question"].lower()
    assert item["skill_id"] != "javascript"


@patch("app.services.path_service.get_groq_response", side_effect=_groq_for_guitar)
@patch("app.services.goal_service.get_groq_response", side_effect=_groq_for_guitar)
def test_guitar_path_uses_llm_resources(mock_goal, mock_path):
    learner = client.post("/api/learner/login", json={"email": "guitar-path@university.edu"}).json()
    client.put(
        f"/api/learner/{learner['id']}",
        json={"goal": "learn guitar in 5 months, 1 hour each day", "duration_months": 5, "hours_per_day": 1},
    )
    path = client.post("/api/path/generate", json={"learner_id": learner["id"]})
    assert path.status_code == 200, path.text
    items = path.json()["items"]
    assert items
    blob = str(items).lower()
    assert "sqlbolt" not in blob
    assert "cs50" not in blob
    assert any("guitar" in (i.get("title") or "").lower() or "justin" in (i.get("title") or "").lower() for i in items)
    assert items[0].get("url")
    assert items[0]["title"] != items[0]["catalog_id"]


@patch("app.services.assessment_service.get_groq_response")
def test_assessment_updates_proficiency(mock_quiz):
    mock_quiz.return_value = {
        "skill_id": "sql",
        "skill": "SQL",
        "difficulty": "easy",
        "question": "Which SQL clause filters rows before grouping?",
        "options": ["WHERE", "HAVING", "LIMIT", "JOIN"],
        "correct": "WHERE",
    }
    learner = client.post("/api/learner/login", json={"email": "quiz@university.edu"}).json()
    client.put(f"/api/learner/{learner['id']}", json={"goal": "Data Analyst", "target_role": "Data Analyst"})
    quiz = client.post("/api/assessment/generate", json={"learner_id": learner["id"]})
    assert quiz.status_code == 200, quiz.text
    items = quiz.json()["items"]
    assert len(items) >= 1
    assert "correct" not in items[0]
    answers = [{"item_id": items[0]["id"], "answer": "WHERE"}]
    submitted = client.post("/api/assessment/submit", json={"assessment_id": quiz.json()["id"], "answers": answers})
    assert submitted.status_code == 200, submitted.text
    skills = submitted.json()["learner"]["skills"]
    assert any(s.get("proficiency", 0) > 0 for s in skills)


@patch("app.services.assessment_service.get_groq_response")
def test_answer_correct_raises_difficulty(mock_quiz):
    def side_effect(prompt, **_kwargs):
        if "Difficulty: medium" in prompt or "difficulty: medium" in prompt.lower():
            return {
                "skill_id": "sql",
                "skill": "SQL",
                "difficulty": "medium",
                "question": "HAVING is applied after which operation?",
                "options": ["GROUP BY", "INSERT", "DROP", "GRANT"],
                "correct": "GROUP BY",
            }
        return {
            "skill_id": "sql",
            "skill": "SQL",
            "difficulty": "easy",
            "question": "SELECT is used to?",
            "options": ["Read rows", "Delete the database", "Create a user", "Grant roles"],
            "correct": "Read rows",
        }

    mock_quiz.side_effect = side_effect
    learner = client.post("/api/learner/login", json={"email": "adaptive@university.edu"}).json()
    client.put(f"/api/learner/{learner['id']}", json={"goal": "Data Analyst", "target_role": "Data Analyst"})
    quiz = client.post("/api/assessment/generate", json={"learner_id": learner["id"]})
    assert quiz.status_code == 200, quiz.text
    current = quiz.json()["current_item"] or quiz.json()["items"][0]
    assert current["difficulty"] == "easy"
    answered = client.post(
        "/api/assessment/answer",
        json={"assessment_id": quiz.json()["id"], "item_id": current["id"], "answer": "Read rows"},
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["correct"] is True
    nxt = answered.json()["next_item"]
    assert nxt
    assert nxt["difficulty"] == "medium"


def test_clarify_vague_goal():
    learner = client.post("/api/learner/login", json={"email": "vague@university.edu"}).json()
    res = client.post(
        "/api/assistant/chat",
        json={"learner_id": learner["id"], "message": "help"},
    )
    assert res.status_code == 200
    assert res.json()["intent"] in ("clarify", "question", "update_profile")


@patch("app.services.chat_service.get_groq_chat", return_value="SQLBolt is first because SQL is a core gap.")
@patch("app.services.chat_service.get_groq_response", return_value={"intent": "question"})
def test_assistant_history(mock_intent, mock_chat):
    learner = client.post("/api/learner/login", json={"email": "chat@university.edu"}).json()
    reply = client.post(
        "/api/assistant/chat",
        json={"learner_id": learner["id"], "message": "Why start with SQL?"},
    )
    assert reply.status_code == 200
    assert reply.json()["intent"] == "question"
    history = client.get(f"/api/assistant/history/{learner['id']}")
    assert history.status_code == 200
    assert len(history.json()["messages"]) >= 2


def test_from_semester_and_role_fit_helpers():
    learner = client.post("/api/learner/login", json={"email": "merge@university.edu", "name": "Merge"}).json()
    sem = client.post(
        f"/api/learner/{learner['id']}/from-semester",
        json={"skills": ["Python", "SQL"], "semester": "Semester 5"},
    )
    assert sem.status_code == 200
    names = [s["name"] for s in sem.json()["skills"]]
    assert "Python" in names

    fit = client.post(
        f"/api/learner/{learner['id']}/from-role-fit",
        json={"target_role": "Data Analyst", "missing_skills": ["Tableau"], "strengths": ["SQL"]},
    )
    assert fit.status_code == 200
    assert fit.json()["target_role"] == "Data Analyst"
    gaps = fit.json()["skill_gaps"]
    blob = str(gaps).lower()
    assert "tableau" in blob
    assert any(isinstance(g, dict) and g.get("skill_id") for g in gaps)


def test_resolve_guitar_topics_are_not_python():
    guitar = client.post("/api/skills/resolve", json={"name": "guitar"})
    python = client.post("/api/skills/resolve", json={"name": "python"})
    assert guitar.status_code == 200, guitar.text
    assert python.status_code == 200, python.text
    guitar_ids = {t["id"] for t in guitar.json()["topics"]}
    python_ids = {t["id"] for t in python.json()["topics"]}
    assert guitar_ids
    assert python_ids
    assert guitar_ids.isdisjoint(python_ids)
    assert any("open-chords" in tid for tid in guitar_ids)
    blob = str(guitar.json()).lower()
    assert "javascript" not in blob
    assert guitar.json()["skill"]["id"] == "guitar"


def test_unmatched_resolve_does_not_enroll_data_analyst():
    from app.services.skill_registry import TaxonomyIn, TopicIn

    fake = TaxonomyIn(
        skill_id="knitting",
        name="Knitting",
        domain="craft",
        topics=[
            TopicIn(id="cast-on", name="Cast on"),
            TopicIn(id="knit-stitch", name="Knit stitch"),
            TopicIn(id="purl", name="Purl stitch"),
        ],
    )
    learner = client.post("/api/learner/login", json={"email": "knit@university.edu"}).json()
    with patch("app.services.skill_registry.generate_taxonomy", return_value=fake):
        resolved = client.post("/api/skills/resolve", json={"name": "knitting", "learner_id": learner["id"]})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["skill"]["id"] != "data-analyst"
    enrolled = client.get(f"/api/learner/{learner['id']}/skills")
    assert enrolled.status_code == 200
    ids = [s["id"] for s in enrolled.json()["skills"]]
    assert "knitting" in ids
    assert "data-analyst" not in ids


@patch("app.services.assessment_service.get_groq_response")
def test_topic_score_updates_mastery(mock_quiz):
    mock_quiz.return_value = {
        "topic_id": "guitar--open-chords",
        "skill_id": "open-chords",
        "skill": "Open chords",
        "difficulty": "easy",
        "question": "Which of these is a standard open guitar chord?",
        "options": ["E major", "H diminished 13", "TCP handshake", "LEFT JOIN"],
        "correct": "E major",
    }
    learner = client.post("/api/learner/login", json={"email": "mastery@university.edu"}).json()
    client.post("/api/skills/resolve", json={"name": "guitar", "learner_id": learner["id"]})
    quiz = client.post("/api/assessment/generate", json={"learner_id": learner["id"], "skill_id": "guitar"})
    assert quiz.status_code == 200, quiz.text
    item = quiz.json()["current_item"] or quiz.json()["items"][0]
    submitted = client.post(
        "/api/assessment/submit",
        json={"assessment_id": quiz.json()["id"], "answers": [{"item_id": item["id"], "answer": "E major"}]},
    )
    assert submitted.status_code == 200, submitted.text
    graph = client.get(f"/api/skills/guitar/graph/{learner['id']}")
    assert graph.status_code == 200
    node = next((n for n in graph.json()["nodes"] if n["id"] == "guitar--open-chords"), None)
    assert node
    assert node["proficiency"] > 0
    assert node["confidence"] > 0


def test_role_fit_gap_analysis_uses_registry_ids():
    learner = client.post("/api/learner/login", json={"email": "gaps-reg@university.edu"}).json()
    res = client.post(
        "/api/role-fit/gap-analysis",
        json={"learner_id": learner["id"], "target_role": "Data Analyst", "missing_skills": ["SQL"]},
    )
    assert res.status_code == 200, res.text
    gaps = res.json()["gaps"]
    assert gaps
    assert gaps[0]["skill_id"] == "dbms"
    enrolled = client.get(f"/api/learner/{learner['id']}/skills")
    ids = [s["id"] for s in enrolled.json()["skills"]]
    assert "dbms" in ids or "data-analyst" in ids


def test_switch_active_skill_between_enrolled():
    learner = client.post("/api/learner/login", json={"email": "switcher@university.edu"}).json()
    client.post("/api/skills/resolve", json={"name": "guitar", "learner_id": learner["id"]})
    client.post("/api/skills/resolve", json={"name": "python", "learner_id": learner["id"]})
    switched = client.put(f"/api/learner/{learner['id']}/active-skill", json={"skill_id": "python"})
    assert switched.status_code == 200, switched.text
    assert switched.json()["active_skill_id"] == "python"
    assert switched.json()["learner"]["active_skill_id"] == "python"
    dash = client.get(f"/api/dashboard/{learner['id']}")
    assert dash.status_code == 200
    assert dash.json()["active_skill_id"] == "python"
    enrolled = client.get(f"/api/learner/{learner['id']}/skills")
    ids = [s["id"] for s in enrolled.json()["skills"]]
    assert "guitar" in ids and "python" in ids
    back = client.put(f"/api/learner/{learner['id']}/active-skill", json={"skill_id": "guitar"})
    assert back.json()["active_skill_id"] == "guitar"


def test_assessment_history_lists_skill():
    learner = client.post("/api/learner/login", json={"email": "hist@university.edu"}).json()
    hist = client.get(f"/api/assessment/history/{learner['id']}")
    assert hist.status_code == 200
    assert "assessments" in hist.json()


@patch("app.services.chat_service.get_groq_chat", return_value="Stay on guitar.")
@patch("app.services.chat_service.get_groq_response", return_value={"intent": "question"})
def test_chat_history_is_per_skill(mock_intent, mock_chat):
    learner = client.post("/api/learner/login", json={"email": "threads@university.edu"}).json()
    client.post("/api/skills/resolve", json={"name": "guitar", "learner_id": learner["id"]})
    client.post("/api/skills/resolve", json={"name": "python", "learner_id": learner["id"]})
    client.put(f"/api/learner/{learner['id']}/active-skill", json={"skill_id": "guitar"})
    client.post("/api/assistant/chat", json={"learner_id": learner["id"], "message": "How do I practice chords?", "skill_id": "guitar"})
    client.post("/api/assistant/chat", json={"learner_id": learner["id"], "message": "Explain list comprehensions.", "skill_id": "python"})
    guitar_hist = client.get(f"/api/assistant/history/{learner['id']}", params={"skill_id": "guitar"})
    python_hist = client.get(f"/api/assistant/history/{learner['id']}", params={"skill_id": "python"})
    assert guitar_hist.status_code == 200
    gblob = str(guitar_hist.json()["messages"]).lower()
    pblob = str(python_hist.json()["messages"]).lower()
    assert "chords" in gblob
    assert "list comprehensions" not in gblob
    assert "list comprehensions" in pblob
    assert "chords" not in pblob


@patch("app.services.chat_service.get_groq_chat", return_value="Separate thread.")
@patch("app.services.chat_service.get_groq_response", return_value={"intent": "question"})
def test_chat_sessions_are_separate(mock_intent, mock_chat):
    learner = client.post("/api/learner/login", json={"email": "chatsplit@university.edu"}).json()
    client.post("/api/skills/resolve", json={"name": "guitar", "learner_id": learner["id"]})
    first = client.post("/api/assistant/sessions", json={"learner_id": learner["id"], "skill_id": "guitar"}).json()
    second = client.post("/api/assistant/sessions", json={"learner_id": learner["id"], "skill_id": "guitar"}).json()
    assert first["id"] != second["id"]
    client.post(
        "/api/assistant/chat",
        json={"learner_id": learner["id"], "message": "How do I tune a guitar?", "session_id": first["id"]},
    )
    client.post(
        "/api/assistant/chat",
        json={"learner_id": learner["id"], "message": "What is a pentatonic scale?", "session_id": second["id"]},
    )
    listed = client.get(f"/api/assistant/sessions/{learner['id']}", params={"skill_id": "guitar"})
    assert listed.status_code == 200
    ids = [s["id"] for s in listed.json()["sessions"]]
    assert first["id"] in ids and second["id"] in ids
    hist_a = client.get(f"/api/assistant/history/{learner['id']}", params={"session_id": first["id"]}).json()
    hist_b = client.get(f"/api/assistant/history/{learner['id']}", params={"session_id": second["id"]}).json()
    blob_a = str(hist_a["messages"]).lower()
    blob_b = str(hist_b["messages"]).lower()
    assert "tune a guitar" in blob_a
    assert "pentatonic" not in blob_a
    assert "pentatonic" in blob_b
    assert "tune a guitar" not in blob_b


def test_resource_agent_keeps_real_urls_and_ratings():
    from types import SimpleNamespace
    from app.services import resource_agent

    def fake_search(query, include_domains=None, **_kwargs):
        if include_domains and "youtube.com" in include_domains:
            return [
                {"title": "Fake clip", "url": "https://www.youtube.com/watch?v=K5Z5Z5Z5", "snippet": "4.9/5 stars", "score": 0.95},
                {
                    "title": "Open chords lesson",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "snippet": "4.8 stars beginner guitar",
                    "score": 0.84,
                },
            ]
        if "textbook" in (query or "").lower() or "book" in (query or "").lower():
            return [
                {
                    "title": "Hal Leonard Guitar Method Book 1",
                    "url": "https://openlibrary.org/search?q=Hal+Leonard+Guitar+Method+Book+1",
                    "snippet": "4.7/5 textbook",
                    "score": 0.72,
                }
            ]
        return [
            {
                "title": "JustinGuitar Beginner Course",
                "url": "https://www.justinguitar.com/guitar-lessons/beginner-guitar-course-grade-1-bc-101",
                "snippet": "rated 4.9/5 by students",
                "score": 0.88,
            }
        ]

    topic = SimpleNamespace(id="guitar--open-chords", name="Open chords", slug="open-chords")
    with patch("app.core.tavily_client.has_tavily", return_value=True), patch(
        "app.core.tavily_client.search", side_effect=fake_search
    ), patch.object(resource_agent, "_native_tool_loop", return_value=None), patch.object(
        resource_agent, "_react_pick", return_value=None
    ):
        found = resource_agent.find_resources(SimpleNamespace(goal="learn guitar"), "guitar", [topic])
    rows = found.get("guitar--open-chords") or []
    urls = [r.get("url") or "" for r in rows]
    assert rows
    assert all("K5Z5Z5Z5" not in u for u in urls)
    assert any("youtube.com/watch?v=dQw4w9WgXcQ" in u for u in urls)
    assert any("justinguitar.com" in u for u in urls)
    assert any(r.get("rating") for r in rows)


def test_broken_resource_urls_are_replaced():
    from app.services.resource_links import looks_broken, normalize_resource

    assert looks_broken("https://www.youtube.com/watch?v=K5Z5Z5Z5")
    assert looks_broken("https://www.justinguitar.com/lessons/lesson-1-1")
    assert not looks_broken("https://www.justinguitar.com/guitar-lessons/beginner-guitar-course-grade-1-bc-101")
    fixed = normalize_resource(
        {
            "title": "Open Chords for Beginners – YouTube",
            "url": "https://www.youtube.com/watch?v=K5Z5Z5Z5",
            "type": "video",
        },
        topic_name="Open chords",
        skill_id="guitar",
    )
    assert fixed["url"].startswith("https://")
    assert "K5Z5Z5Z5" not in fixed["url"]
    book = normalize_resource(
        {
            "title": "Hal Leonard Guitar Method Book 1",
            "url": "https://www.amazon.com/Hal-Leonard-Guitar-Method-Book/dp/0735217729",
            "type": "textbook",
        },
        topic_name="Open chords",
        skill_id="guitar",
    )
    assert "0735217729" not in book["url"]
    assert book["url"].startswith("https://")


def test_guitar_graph_has_major_topics():
    learner = client.post("/api/learner/login", json={"email": "ggraph@university.edu"}).json()
    client.post("/api/skills/resolve", json={"name": "guitar", "learner_id": learner["id"]})
    graph = client.get(f"/api/skills/guitar/graph/{learner['id']}")
    assert graph.status_code == 200, graph.text
    nodes = graph.json()["nodes"]
    majors = [n for n in nodes if n.get("kind") == "major"]
    leaves = [n for n in nodes if n.get("kind") == "topic"]
    assert majors
    assert leaves
    assert any(n.get("parent_id") for n in leaves)


@patch("app.services.path_service.get_groq_response", side_effect=_groq_for_guitar)
def test_path_resources_have_about_and_more_endpoint(mock_path):
    learner = client.post("/api/learner/login", json={"email": "resmore@university.edu"}).json()
    client.post("/api/skills/resolve", json={"name": "guitar", "learner_id": learner["id"]})
    path = client.post("/api/path/generate", json={"learner_id": learner["id"]})
    assert path.status_code == 200, path.text
    items = path.json()["items"]
    assert items
    assert items[0].get("resources")
    assert any(r.get("about") or r.get("why") for r in items[0]["resources"])
    topic_id = items[0]["topic_id"]
    more = client.post("/api/path/resources", json={"learner_id": learner["id"], "topic_id": topic_id})
    assert more.status_code == 200, more.text
    nxt = next(i for i in more.json()["items"] if i["topic_id"] == topic_id)
    assert len(nxt.get("resources") or []) >= len(items[0]["resources"])


def test_semester_roadmap_includes_resources():
    learner = client.post("/api/learner/login", json={"email": "semres@university.edu"}).json()
    sem = client.post(
        f"/api/learner/{learner['id']}/from-semester",
        json={"skills": ["Python"], "semester": "Semester 3"},
    )
    assert sem.status_code == 200
    road = client.get(f"/api/semester/roadmap/{learner['id']}")
    assert road.status_code == 200
    subjects = road.json()["subjects"]
    assert subjects
    assert any(s.get("resources") for s in subjects)


@patch("app.services.role_fit_service.get_groq_response", return_value=MOCK_ROLE_FIT_RESPONSE)
def test_role_fit_jd_resume_returns_jobs(mock_groq):
    learner = client.post("/api/learner/login", json={"email": "jd@university.edu"}).json()
    res = client.post(
        "/api/role-fit/analyze",
        json={
            "target_role": "Backend Dev",
            "current_skills": ["Python"],
            "job_description": "Need Python and APIs",
            "resume_text": "Built APIs in Python",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["recommended_jobs"]
    assert body["recommended_jobs"][0]["title"]
    gaps = client.post(
        "/api/role-fit/gap-analysis",
        json={"learner_id": learner["id"], "target_role": "Backend Dev", "missing_skills": body["missing_skills"]},
    )
    assert gaps.status_code == 200
    assert any(g.get("skill_id") for g in gaps.json()["gaps"])


if __name__ == "__main__":
    tests = [
        test_semester_analyze,
        test_resume_generate,
        test_role_fit_analyze,
        test_roadmap_generate,
        test_login_and_profile_roundtrip,
        test_catalog_lists_resources,
        test_path_generate_complete_and_adapt,
        test_assistant_history,
        test_from_semester_and_role_fit_helpers,
        test_skill_graph_and_gaps,
        test_ranking_prefers_free_handson,
        test_unmatched_goal_not_analyst,
        test_guitar_assessment_is_not_programming,
        test_guitar_path_uses_llm_resources,
        test_assessment_updates_proficiency,
        test_answer_correct_raises_difficulty,
        test_clarify_vague_goal,
        test_resolve_guitar_topics_are_not_python,
        test_unmatched_resolve_does_not_enroll_data_analyst,
        test_topic_score_updates_mastery,
        test_role_fit_gap_analysis_uses_registry_ids,
        test_switch_active_skill_between_enrolled,
        test_assessment_history_lists_skill,
        test_chat_history_is_per_skill,
        test_chat_sessions_are_separate,
        test_resource_agent_keeps_real_urls_and_ratings,
        test_broken_resource_urls_are_replaced,
        test_guitar_graph_has_major_topics,
        test_path_resources_have_about_and_more_endpoint,
        test_semester_roadmap_includes_resources,
        test_role_fit_jd_resume_returns_jobs,
    ]
    for test in tests:
        test()
        print(f"{test.__name__}: PASSED")
    print("All tests PASSED")
