import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core import tavily_client
from app.core.groq_client import _extract_json, get_groq_response, get_groq_with_tools
from app.services import resource_links

logger = logging.getLogger(__name__)

COURSE_DOMAINS = {
    "justinguitar.com",
    "andyguitar.co.uk",
    "freecodecamp.org",
    "coursera.org",
    "khanacademy.org",
    "edx.org",
    "udemy.com",
    "fender.com",
    "musictheory.net",
    "theodinproject.com",
    "kaggle.com",
    "developer.mozilla.org",
}
BOOK_DOMAINS = {
    "openlibrary.org",
    "halleonard.com",
    "penguinrandomhouse.com",
    "amazon.com",
    "archive.org",
    "goodreads.com",
    "worldcat.org",
}
RATING_RE = re.compile(r"(\d(?:\.\d)?)\s*(?:/\s*5|stars?)", re.I)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_courses",
            "description": "Search the web for real online courses for a topic.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_youtube",
            "description": "Search YouTube for a real lesson video about a topic.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": "Search for well-rated textbooks or method books.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


def has_tavily() -> bool:
    return tavily_client.has_tavily()


def rating_label(snippet: str, score: float) -> tuple[str, str]:
    match = RATING_RE.search(snippet or "")
    if match:
        return f"{match.group(1)}/5", "snippet"
    pct = int(round((score or 0) * 100))
    if pct >= 70:
        return f"High match {pct}%", "tavily"
    if pct > 0:
        return f"Match {pct}%", "tavily"
    return "", ""


def _keep_hit(hit: dict, kind: str) -> bool:
    url = hit.get("url") or ""
    if resource_links.looks_broken(url):
        return False
    host = resource_links.hostname(url)
    if kind == "video":
        if "youtube.com" not in host and "youtu.be" not in host:
            return False
        vid = resource_links.youtube_id(url)
        if vid and resource_links.looks_broken(url):
            return False
        return bool(vid or "/@" in url or "/results" in url)
    if kind == "course" and ("youtube.com" in host or "youtu.be" in host):
        return False
    return True


def _score_hit(hit: dict, kind: str) -> float:
    url = hit.get("url") or ""
    host = resource_links.hostname(url)
    score = float(hit.get("score") or 0)
    if kind == "course" and host in COURSE_DOMAINS:
        score += 0.25
    if kind == "textbook" and host in BOOK_DOMAINS:
        score += 0.25
    if kind == "video" and resource_links.youtube_id(url):
        score += 0.2
    stars, _ = rating_label(hit.get("snippet") or "", hit.get("score") or 0)
    if "/5" in stars:
        try:
            score += float(stars.split("/")[0]) / 10
        except ValueError:
            pass
    return score


def run_tool(name: str, query: str) -> List[dict]:
    kind = {"search_courses": "course", "search_youtube": "video", "search_books": "textbook"}.get(name, "website")
    include = ["youtube.com"] if name == "search_youtube" else None
    hits = tavily_client.search(query, include_domains=include)
    out = []
    for hit in hits:
        row = {**hit, "type": kind}
        if not _keep_hit(row, kind):
            continue
        rating, source = rating_label(row.get("snippet") or "", row.get("score") or 0)
        row["rating"] = rating
        row["rating_source"] = source
        row["quality"] = _score_hit(row, kind)
        out.append(row)
    out.sort(key=lambda r: -r.get("quality", 0))
    return out[:5]


def _hit_to_resource(hit: dict, topic_id: str, topic_name: str) -> dict:
    kind = hit.get("type") or "website"
    rating, source = hit.get("rating") or "", hit.get("rating_source") or ""
    if not rating:
        rating, source = rating_label(hit.get("snippet") or "", hit.get("score") or 0)
    about = (hit.get("snippet") or "").strip()
    if len(about) > 220:
        about = about[:217] + "..."
    return {
        "topic_id": topic_id,
        "title": hit.get("title") or topic_name,
        "url": hit.get("url") or "",
        "type": kind,
        "rating": rating,
        "rating_source": source,
        "about": about or f"{kind.title()} for {topic_name}.",
        "why": f"Found via live search for {topic_name}.",
    }


def _heuristic_pick(topic, pools: Dict[str, List[dict]]) -> List[dict]:
    picked = []
    for kind in ("course", "video", "textbook"):
        rows = pools.get(kind) or []
        if rows:
            picked.append(_hit_to_resource(rows[0], topic.id, topic.name))
    return picked


def _pools_from_hits(hits: List[dict]) -> Dict[str, List[dict]]:
    pools: Dict[str, List[dict]] = {"course": [], "video": [], "textbook": []}
    for hit in hits:
        kind = hit.get("type") or "website"
        if kind in pools:
            pools[kind].append(hit)
    return pools


def _default_searches(topic_name: str, skill_id: str) -> List[tuple[str, str]]:
    focus = f"{topic_name} {skill_id}".strip()
    return [
        ("search_courses", f"{focus} free official course"),
        ("search_youtube", f"{focus} beginner lesson youtube"),
        ("search_books", f"{focus} textbook book best rated"),
    ]


def _react_pick(learner, skill_id: str, topic, hits: List[dict]) -> Optional[List[dict]]:
    blob = [
        {
            "title": h.get("title"),
            "url": h.get("url"),
            "type": h.get("type"),
            "rating": h.get("rating"),
            "score": round(h.get("quality") or h.get("score") or 0, 3),
            "snippet": (h.get("snippet") or "")[:180],
        }
        for h in hits[:12]
    ]
    prompt = f"""
Pick the best real learning resources from SEARCH RESULTS only. Do not invent URLs.

Skill: {skill_id}
Topic id: {topic.id}
Topic name: {topic.name}
Goal: {getattr(learner, "goal", "")}

Results: {json.dumps(blob)}

Return JSON:
{{"tool": null, "query": null, "resources":[{{"topic_id":"{topic.id}","title":"...","url":"https://...","type":"course|video|textbook","rating":"...","about":"...","why":"..."}}]}}
Need one course, one YouTube video, and one textbook when those types exist in results.
If you need another search instead, return {{"tool":"search_courses|search_youtube|search_books","query":"...","resources":[]}}
"""
    try:
        data = get_groq_response(prompt)
    except Exception:
        return None
    tool = (data.get("tool") or "").strip()
    query = (data.get("query") or "").strip()
    if tool in ("search_courses", "search_youtube", "search_books") and query:
        extra = run_tool(tool, query)
        hits.extend(extra)
        return None
    rows = []
    for row in data.get("resources") or []:
        if not isinstance(row, dict) or not row.get("url") or not row.get("title"):
            continue
        if resource_links.looks_broken(row.get("url") or ""):
            continue
        kind = str(row.get("type") or "website").lower()
        if kind in ("youtube", "lesson"):
            kind = "video"
        rating = row.get("rating") or ""
        source = "snippet" if rating and "/5" in str(rating) else ("tavily" if rating else "")
        rows.append(
            {
                "topic_id": topic.id,
                "title": row["title"],
                "url": row["url"],
                "type": kind,
                "rating": rating,
                "rating_source": source,
                "about": row.get("about") or "",
                "why": row.get("why") or f"Selected for {topic.name}.",
            }
        )
    return rows or None


def _native_tool_loop(learner, skill_id: str, topic, hits: List[dict]) -> Optional[List[dict]]:
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You find real courses, YouTube videos, and textbooks. "
                "Use the tools. Never invent URLs. When done, reply with JSON only: "
                '{"resources":[{"topic_id":"","title":"","url":"https://","type":"course|video|textbook","rating":"","about":"","why":""}]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Find one course, one YouTube video, and one textbook for topic {topic.name} "
                f"(id {topic.id}) in skill {skill_id}. Goal: {getattr(learner, 'goal', '')}."
            ),
        },
    ]
    try:
        for _ in range(4):
            msg = get_groq_with_tools(messages, TOOL_SCHEMAS)
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                            }
                            for tc in tool_calls
                        ],
                    }
                )
                for tc in tool_calls:
                    args = {}
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        pass
                    found = run_tool(tc.function.name, str(args.get("query") or topic.name))
                    hits.extend(found)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(
                                [{"title": h["title"], "url": h["url"], "type": h["type"], "rating": h.get("rating"), "score": h.get("score")} for h in found]
                            ),
                        }
                    )
                continue
            text = msg.content or ""
            if not text:
                return None
            data = _extract_json(text)
            rows = []
            for row in data.get("resources") or []:
                if not isinstance(row, dict) or not row.get("url"):
                    continue
                if resource_links.looks_broken(row.get("url") or ""):
                    continue
                rows.append(
                    {
                        "topic_id": topic.id,
                        "title": row.get("title") or topic.name,
                        "url": row["url"],
                        "type": row.get("type") or "website",
                        "rating": row.get("rating") or "",
                        "rating_source": "snippet" if row.get("rating") else "",
                        "about": row.get("about") or "",
                        "why": row.get("why") or "",
                    }
                )
            return rows or None
    except Exception as exc:
        logger.info("Groq native tools unavailable: %s", exc)
    return None


def _agent_for_topic(learner, skill_id: str, topic) -> List[dict]:
    hits: List[dict] = []
    for tool, query in _default_searches(topic.name, skill_id):
        hits.extend(run_tool(tool, query))

    picked = _native_tool_loop(learner, skill_id, topic, hits)
    if not picked:
        for _ in range(2):
            react = _react_pick(learner, skill_id, topic, hits)
            if react:
                picked = react
                break
    if not picked:
        picked = _heuristic_pick(topic, _pools_from_hits(hits))

    seen = set()
    out = []
    for row in picked:
        key = row.get("url") or row.get("title")
        if not key or key in seen or resource_links.looks_broken(row.get("url") or ""):
            continue
        seen.add(key)
        out.append(row)
    return out[:4]


def find_resources(learner, skill_id: str, topics) -> dict:
    """Search Tavily (via the resource agent) and return {topic_id: [resources]}."""
    if not topics:
        return {}
    bundled: Dict[str, List[dict]] = {}
    for topic in topics:
        try:
            rows = _agent_for_topic(learner, skill_id, topic)
        except Exception as exc:
            logger.warning("Resource agent failed for %s: %s", getattr(topic, "id", topic), exc)
            rows = []
        bundled[topic.id] = resource_links.normalize_resources(rows, topic_name=topic.name, skill_id=skill_id)
    return bundled
