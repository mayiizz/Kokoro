import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests

logger = logging.getLogger(__name__)

UA = {"User-Agent": "Mozilla/5.0 (compatible; Kokoro/1.0; +https://localhost)"}
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_VERIFIED: Optional[List[dict]] = None


def _verified() -> List[dict]:
    global _VERIFIED
    if _VERIFIED is None:
        path = Path(__file__).resolve().parent.parent / "data" / "verified_resources.json"
        try:
            _VERIFIED = json.loads(path.read_text()).get("resources") or []
        except Exception:
            _VERIFIED = []
    return _VERIFIED


def hostname(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def youtube_id(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    host = (parsed.netloc or "").lower()
    if "youtu.be" in host:
        return (parsed.path or "").strip("/").split("/")[0]
    if "youtube.com" in host:
        if parsed.path.startswith("/watch"):
            return (parse_qs(parsed.query).get("v") or [""])[0]
        parts = [p for p in parsed.path.split("/") if p]
        if parts and parts[0] in ("embed", "shorts", "live") and len(parts) > 1:
            return parts[1]
    return ""


def looks_broken(url: str) -> bool:
    raw = (url or "").strip()
    if not raw or raw == "#" or not raw.startswith("http"):
        return True
    parsed = urlparse(raw)
    if not parsed.netloc or "." not in parsed.netloc:
        return True
    if any(host in parsed.netloc for host in ("localhost", "example.com", "invalid")):
        return True
    vid = youtube_id(raw)
    if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
        if parsed.path.startswith("/results") or parsed.path.startswith("/@"):
            return False
        if vid:
            if not YT_ID.match(vid):
                return True
            compact = re.sub(r"[^A-Za-z0-9]", "", vid)
            if len(set(compact.lower())) <= 3:
                return True
    if re.search(r"(Z5Z5|K5Z5|Y5Z5|XXX|placeholder|lesson-1-1)", raw, re.I):
        return True
    if "justinguitar.com" in parsed.netloc and "/lessons/" in parsed.path and "/guitar-lessons/" not in parsed.path:
        return True
    return False


def search_fallback(title: str, rtype: str, topic_name: str = "") -> str:
    q = " ".join(part for part in (title, topic_name) if part).strip() or topic_name or title
    kind = (rtype or "website").lower()
    if kind in ("video", "youtube"):
        return f"https://www.youtube.com/results?search_query={quote_plus(q)}"
    if kind == "textbook":
        return f"https://www.amazon.com/s?k={quote_plus(q + ' book')}"
    if kind == "course":
        return f"https://www.google.com/search?q={quote_plus(q + ' free course')}"
    return f"https://www.google.com/search?q={quote_plus(q)}"


def search_web(query: str, limit: int = 6) -> List[str]:
    if os.getenv("ACADBRIDGE_SKIP_URL_FETCH") == "1":
        return []
    try:
        res = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=UA,
            timeout=8,
        )
        res.raise_for_status()
        hrefs = re.findall(r'href="([^"]+)"', res.text)
        out: List[str] = []
        for href in hrefs:
            url = href
            if "uddg=" in href:
                url = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
            if url.startswith("//"):
                url = "https:" + url
            if not url.startswith("http"):
                continue
            host = hostname(url)
            if not host or "duckduckgo.com" in host:
                continue
            if looks_broken(url):
                continue
            if url not in out:
                out.append(url)
            if len(out) >= limit:
                break
        return out
    except Exception as exc:
        logger.info("Web search failed for %s: %s", query, exc)
        return []


def youtube_exists(url: str) -> bool:
    vid = youtube_id(url)
    if not vid or not YT_ID.match(vid):
        return False
    if os.getenv("ACADBRIDGE_SKIP_URL_FETCH") == "1":
        return not looks_broken(url)
    try:
        res = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"},
            headers=UA,
            timeout=6,
        )
        return res.status_code == 200
    except Exception:
        return False


def url_exists(url: str) -> bool:
    if looks_broken(url):
        return False
    if youtube_id(url):
        return youtube_exists(url)
    parsed = urlparse(url)
    if parsed.path.startswith("/results") or parsed.path.startswith("/@"):
        return True
    if os.getenv("ACADBRIDGE_SKIP_URL_FETCH") == "1":
        return True
    try:
        res = requests.head(url, allow_redirects=True, timeout=6, headers=UA)
        if res.status_code in (400, 403, 405, 501):
            if res.status_code == 403 and hostname(url) in {"justinguitar.com", "amazon.com"}:
                return True
            res = requests.get(url, allow_redirects=True, timeout=6, headers=UA, stream=True)
        if res.status_code == 403 and hostname(url) in {"justinguitar.com", "amazon.com"}:
            return True
        return 200 <= res.status_code < 400
    except Exception:
        return False


def _blob(*parts: str) -> str:
    return " ".join(str(p or "").lower() for p in parts)


def curated_match(topic_name: str, rtype: str, title: str = "", skill_id: str = "") -> Optional[dict]:
    blob = _blob(topic_name, title, skill_id)
    kind = (rtype or "").lower()
    best = None
    best_score = 0
    for row in _verified():
        keys = [k.lower() for k in (row.get("keywords") or [])]
        hits = sum(1 for k in keys if k in blob)
        if hits <= 0:
            continue
        types = [t.lower() for t in (row.get("types") or [])]
        type_bonus = 2 if kind and kind in types else 0
        score = hits + type_bonus
        if score > best_score:
            best_score = score
            best = row
    if not best:
        return None
    return {
        "title": best.get("title") or title,
        "url": best["url"],
        "type": kind or (best.get("types") or ["website"])[0],
        "about": best.get("about") or "",
    }


def _prefer_url(candidates: List[str], rtype: str) -> str:
    kind = (rtype or "").lower()
    ranked = []
    for url in candidates:
        host = hostname(url)
        score = 0
        if kind in ("video", "youtube") and ("youtube.com" in host or "youtu.be" in host):
            score += 5
            if youtube_id(url) and youtube_exists(url):
                score += 5
        if kind == "textbook" and any(h in host for h in ("halleonard.com", "penguinrandomhouse.com", "amazon.com", "openlibrary.org", "archive.org")):
            score += 5
        if kind == "course" and any(h in host for h in ("justinguitar.com", "andyguitar.co.uk", "fender.com", "coursera.org", "khanacademy.org", "freecodecamp.org")):
            score += 5
        if looks_broken(url):
            continue
        ranked.append((score, url))
    ranked.sort(key=lambda x: -x[0])
    return ranked[0][1] if ranked else ""


_GUESSED_HOSTS = {"amazon.com", "udemy.com", "guitartricks.com", "guitarlessons.com", "guitarworld.com"}


def resolve_url(title: str, url: str, rtype: str, topic_name: str = "", skill_id: str = "") -> str:
    current = (url or "").strip()
    curated = curated_match(topic_name, rtype, title, skill_id)
    if curated and curated.get("url") and not looks_broken(curated["url"]):
        if not current or looks_broken(current) or hostname(current) in _GUESSED_HOSTS:
            return curated["url"]
    if current and not looks_broken(current) and hostname(current) not in _GUESSED_HOSTS:
        return current
    if curated and curated.get("url") and not looks_broken(curated["url"]):
        return curated["url"]
    queries = [
        f"{title} {topic_name} {rtype}".strip(),
        f"{topic_name} {skill_id} {rtype} official".strip(),
    ]
    if (rtype or "").lower() in ("video", "youtube"):
        queries.insert(0, f"{topic_name or title} {skill_id} lesson site:youtube.com")
    if (rtype or "").lower() == "textbook":
        queries.insert(0, f"{title or topic_name} book official")
    found: List[str] = []
    for query in queries:
        found.extend(search_web(query))
        picked = _prefer_url(found, rtype)
        if picked:
            return picked
    return search_fallback(title, rtype, topic_name)


def normalize_resource(row: dict, topic_name: str = "", skill_id: str = "") -> dict:
    out = dict(row or {})
    rtype = str(out.get("type") or "website").lower()
    if rtype in ("youtube", "lesson"):
        rtype = "video"
    title = str(out.get("title") or topic_name or "Resource")
    url = resolve_url(title, str(out.get("url") or ""), rtype, topic_name, skill_id)
    out["title"] = title
    out["url"] = url
    out["type"] = rtype
    if not out.get("about"):
        out["about"] = out.get("why") or f"Open this {rtype} to practice {topic_name or title}."
    return out


def normalize_resources(rows: List[dict], topic_name: str = "", skill_id: str = "") -> List[dict]:
    seen = set()
    out = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        fixed = normalize_resource(row, topic_name=topic_name, skill_id=skill_id)
        key = fixed.get("url") or fixed.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        fixed["rank"] = len(out) + 1
        out.append(fixed)
    return out
