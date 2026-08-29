# Kokoro — Product Requirements Document

**Product:** Kokoro (心)  
**Type:** AI-powered personalized learning-path recommender  
**Status:** Working prototype  
**Document version:** 1.0  
**Last updated:** 30 August 2026

---

## 1. Overview

Kokoro helps a learner go from “I want to learn X” to a sequenced, skill-scoped path of real courses, videos, books, projects, and assessments. The product stores a learner profile, measures topic-level mastery, and adapts the remaining path as the learner completes work or gives feedback.

The name **Kokoro** (心) means heart, mind, or spirit. The product’s job is to keep learning focused on one skill at a time, with a clear next step.

### 1.1 Problem

Self-directed learners get lost between generic roadmaps, hallucinated course links, and tools that mix every interest into one blob.

Typical failures:

- A guitar learner is shown an Excel or analyst path from an old goal.
- Chat history and progress from one skill leak into another.
- LLM-generated YouTube or lesson URLs are fake or 404.
- There is no simple way to switch skills the way Duolingo switches languages.
- Completing a video is treated as mastery, even when the learner cannot pass a topic quiz.

### 1.2 Solution

Kokoro is a **skill-scoped learning OS**:

1. The learner states a goal in chat or enrolls a skill from the header switcher.
2. The system resolves that goal to a catalog skill and a topic graph.
3. An assessment (optional but recommended) sets topic proficiency.
4. A path is generated for **that skill only**, with real resource URLs.
5. Dashboard, chat, path, and assessment all follow the **active skill**.
6. Feedback (done / too hard / not relevant) regenerates the remaining steps.

### 1.3 Product principles

| Principle | Meaning |
|-----------|---------|
| One active skill | Path, chat, and assessment never leak another skill’s content. |
| Real links only | Resources must be catalog, curated, or live-search verified — not invented IDs. |
| Mastery ≠ completion | Topic proficiency comes from assessment evidence, not only “marked done.” |
| Explain the order | Every path item has a “why” tied to gaps and prerequisites. |
| Stay lightweight | Vite + FastAPI + SQLite + Groq. No forced move to Next.js, Postgres, Neo4j, or JWT. |

---

## 2. Goals and non-goals

### 2.1 Goals

- Let a learner enroll multiple skills and switch the active one from any page.
- Generate a sequenced path (prerequisites → topics → projects → assessments).
- Attach real, openable resources (courses, YouTube, textbooks) with ratings when available.
- Persist profile, paths, chats, assessments, and mastery in SQLite.
- Adapt the remaining path after feedback without rewriting completed items.
- Keep Semester Mapping, Role Fit, and ATS Resume as **inputs / utilities**, not the core loop.

### 2.2 Non-goals (this phase)

- Production auth (passwords, OAuth, JWT).
- Multi-tenant orgs, classrooms, or teacher dashboards.
- Paid marketplace or affiliate checkout.
- Mobile native apps.
- Migrating off Vite / FastAPI / SQLite / Groq unless explicitly requested.

---

## 3. Users

| Persona | Need | How Kokoro helps |
|---------|------|------------------|
| Self-taught learner | “I want to learn guitar / Python / ML.” | Goal → skill → path → next action. |
| Student with a syllabus | “Map my semester subjects to industry skills.” | Semester Mapping writes skills into the profile. |
| Career switcher | “What do I lack for data analyst?” | Role Fit saves target role and gaps used by the path. |
| Multi-interest learner | “I study guitar and also want Python.” | Skill switcher + per-skill paths and chats. |

**Primary user for v1:** an individual learner on desktop, signing in with email only.

---

## 4. Product surface

### 4.1 Information architecture

| Route | Page | Role |
|-------|------|------|
| `/` | Landing | Brand, value prop, CTA |
| `/login` | Login | Email (+ optional name) creates or loads a learner |
| `/home` | Dashboard | Active skill cards, streak, next action |
| `/home/assistant` | Assistant | Multi-thread chat, skill-scoped |
| `/home/assessment` | Assessment | Generate, take, and review quizzes |
| `/home/graph` | Skill Graph | Prerequisite / topic map + mastery |
| `/home/path` | Learning Path | Sequenced items, resources, feedback |
| `/home/profile` | Profile | Goals, hours, skills, completed courses |
| `/home/semester` | Semester Mapping | Syllabus → skills |
| `/home/role-fit` | Role Fit | Target role + gap analysis |
| `/home/resume` | ATS Resume | Resume draft / PDF (utility) |

Header (all `/home` pages): **skill switcher**, learner name, profile.

Sidebar: navigation + Kokoro lockup (心 + name).

### 4.2 Brand

- Product name: **Kokoro**
- Mark: the character **心**
- Landing / login / app: faint calligraphy of 心 as a **fixed** background (does not scale with fullscreen; content scrolls over it)
- Do not use “心 (こころ / Kokoro)” as repeated subtitle copy

---

## 5. Core user journeys

### 5.1 First session

```
Landing → Get Started → Login (email)
  → Dashboard (empty or last skill)
  → Assistant: “I want to learn guitar, 1 hour a day”
  → System resolves skill, enrolls it, sets active_skill_id
  → Optional assessment
  → Generate path
  → Dashboard shows skill card + next action
```

### 5.2 Daily loop

```
Open app (same email) → confirm active skill
  → Do next path item (open resource)
  → Mark complete or “too hard”
  → Path adapts remaining items
  → Streak updates if they were active today
```

### 5.3 Switch skill (Duolingo-style)

```
Header switcher → pick enrolled skill
  OR “Learn another skill” (Guitar, Python, Frontend, ML, Data Analyst, DBMS, or free text)
  → resolve skill → set active_skill_id
  → Dashboard, Path, Chat, Assessment reload for that skill only
```

### 5.4 Academic / career inputs

```
Semester Mapping → analyze syllabus → merge skills into profile
Role Fit → analyze role → save target_role + skill_gaps
  → Path generator uses those gaps when relevant to the active skill
```

---

## 6. Functional requirements

### 6.1 Identity and session

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTH-1 | Sign in with email only. No password. | P0 |
| AUTH-2 | Same email loads the existing learner. | P0 |
| AUTH-3 | Session is stored in `localStorage` (learner id). Logout clears it. | P0 |
| AUTH-4 | Unauthenticated `/home/*` redirects to `/login`. | P0 |

### 6.2 Learner profile

| ID | Requirement | Priority |
|----|-------------|----------|
| PROF-1 | Persist name, email, experience, interests, goal, hours, budget, preference. | P0 |
| PROF-2 | Persist skills, target role, skill gaps, completed courses. | P0 |
| PROF-3 | Persist `active_skill_id`, streak days, last active date. | P0 |
| PROF-4 | Semester and Role Fit can write into the same profile. | P1 |

### 6.3 Skills and active skill

| ID | Requirement | Priority |
|----|-------------|----------|
| SKL-1 | Resolve a free-text goal or chip to a canonical skill id. | P0 |
| SKL-2 | Enroll a skill (`LearnerSkill`) when the learner starts it. | P0 |
| SKL-3 | Header switcher lists enrolled skills and sets `active_skill_id`. | P0 |
| SKL-4 | “Learn another skill” supports suggested chips + custom text. | P0 |
| SKL-5 | Dashboard, path, chat, and assessment are scoped to the active skill. | P0 |
| SKL-6 | A path fetch in strict mode must never return another skill’s path. | P0 |

### 6.4 Skill graph and mastery

| ID | Requirement | Priority |
|----|-------------|----------|
| GRPH-1 | Each skill has topics with prerequisites and a required score. | P0 |
| GRPH-2 | Learner topic mastery is stored separately from path completion. | P0 |
| GRPH-3 | Skill Graph page visualizes topics and current proficiency. | P1 |
| GRPH-4 | Path order respects prerequisites and current gaps. | P0 |

### 6.5 Assessment

| ID | Requirement | Priority |
|----|-------------|----------|
| ASM-1 | Generate a short multiple-choice assessment for the active skill. | P0 |
| ASM-2 | Save answers, score items, update topic mastery on submit. | P0 |
| ASM-3 | Show assessment history as cards with skill name (not raw ids). | P1 |
| ASM-4 | History is filterable / attributable to a skill. | P1 |

### 6.6 Learning path

| ID | Requirement | Priority |
|----|-------------|----------|
| PATH-1 | Generate a sequenced path for the active skill only. | P0 |
| PATH-2 | Each item has type, title, why, phase/week, and resources. | P0 |
| PATH-3 | Learner can mark complete, skip, too hard, or not relevant. | P0 |
| PATH-4 | Adapt regenerates **remaining** items; completed stay. | P0 |
| PATH-5 | UI reloads when `active_skill_id` changes. | P0 |
| PATH-6 | Resource cards show a working link and optional rating. | P0 |
| PATH-7 | Broken / invented URLs are repaired or replaced before display. | P0 |

### 6.7 Resource discovery

| ID | Requirement | Priority |
|----|-------------|----------|
| RES-1 | Prefer catalog + curated verified resources. | P0 |
| RES-2 | If `TAVILY_API_KEY` is set, a resource agent searches live courses, YouTube, and books. | P1 |
| RES-3 | Agent tools: `search_courses`, `search_youtube`, `search_books`. | P1 |
| RES-4 | Keep real URLs; never ship placeholder YouTube ids or 404 slugs. | P0 |
| RES-5 | Ratings may come from snippet text (e.g. 4.8/5) or search relevance. | P2 |
| RES-6 | Without Tavily, fall back to Groq + curated JSON + catalog. | P0 |

### 6.8 Assistant

| ID | Requirement | Priority |
|----|-------------|----------|
| CHAT-1 | Conversational goal capture and Q&A about the current path. | P0 |
| CHAT-2 | Multiple chat threads per learner (and per skill). | P0 |
| CHAT-3 | “New chat” starts a fresh thread; sidebar lists threads with preview. | P0 |
| CHAT-4 | Assistant must not invent catalog items or claim it wrote proficiency. | P0 |
| CHAT-5 | Assistant identity is Kokoro. | P1 |

### 6.9 Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| DASH-1 | Show enrolled skills as cards (not a `<select>`). | P0 |
| DASH-2 | Stats: skills at target, path %, streak, next topic. | P0 |
| DASH-3 | Open path / open chat from a skill card. | P0 |
| DASH-4 | If enrolled list is empty but a goal exists, offer enroll from goal. | P1 |
| DASH-5 | Reload when active skill changes. | P0 |

### 6.10 Adjacent modules

| ID | Requirement | Priority |
|----|-------------|----------|
| SEM-1 | Analyze a syllabus / semester and extract skills. | P1 |
| SEM-2 | Merge those skills into the learner profile. | P1 |
| ROLE-1 | Analyze fit for a target role and persist gaps. | P1 |
| CV-1 | Generate an ATS-oriented resume / PDF. | P2 |

---

## 7. AI / ML behavior

Kokoro is not a generic chatbot wrapper. AI is used in specific jobs:

| Job | Model / tool | Constraint |
|-----|--------------|------------|
| Goal → skill resolve | Groq | Must map to a known or newly resolved skill id |
| Path ranking / explanations | Groq + catalog / graph | Do not invent courses |
| Chat | Groq, one call per message | Path-aware, no fake catalog writes |
| Assessment questions | Groq | Tied to skill topics |
| Resource agent | Groq tool loop + Tavily | Live search; keep real URLs |
| URL repair | Heuristics + curated JSON + search fallback | Drop broken links |
| Semester / role-fit analysis | Groq | Writes structured profile fields |

**Fallback:** if Groq is missing, path generation uses a catalog heuristic. If Tavily is missing, resources use curated / catalog only.

**Default chat/path model:** Groq (`openai/gpt-oss-20b` unless overridden in env).

---

## 8. Data and persistence

**Store:** SQLite (`backend/acadbridge.db`).

**Important entities:**

- `Learner` — profile, goal, active skill, streak
- `LearnerSkill` / `LearnerTopicMastery` — enrollment and topic scores
- `Skill` / `SkillTopic` — taxonomy and prerequisites
- `LearningPath` / `PathItem` — skill-scoped roadmap
- `Assessment` / `AssessmentItem` — quizzes and answers
- `ChatSession` / `ChatMessage` — threaded assistant history
- `AcademicProfile` / `AcademicSubject` — semester mapping
- Catalog JSON + `verified_resources.json` — static / curated content

Secrets (`GROQ_API_KEY`, `TAVILY_API_KEY`) live in `backend/.env` and must never be committed.

---

## 9. Technical architecture

```
Browser (Vite + React + TS, :8080)
        │  REST JSON
        ▼
FastAPI (:8000)
  ├── routes/     learner, path, assistant, assessment, skills, dashboard, …
  ├── services/   path, chat, resource agent, resource link repair
  ├── core/       Groq client, Tavily client
  └── data/       catalog.json, verified_resources.json
        │
        ▼
SQLite
```

| Layer | Choice | Notes |
|-------|--------|-------|
| Frontend | Vite, React, TypeScript, Tailwind, shadcn | Port 8080 |
| Backend | FastAPI, SQLAlchemy, Pydantic | Port 8000 |
| LLM | Groq | Required for live AI |
| Search | Tavily (optional) | ~1 credit per basic search |
| Auth | Email + localStorage | Prototype only |

---

## 10. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Local demo: frontend and backend start with documented commands. |
| NFR-2 | Backend wiring tests cover skill switch, path scoping, resource agent URL honesty. |
| NFR-3 | Path/chat for skill A must not display skill B’s items after a switch. |
| NFR-4 | Resource links should open a real host (or be stripped). |
| NFR-5 | UI copy uses **Kokoro** / **心**; no leftover AcadBridge in user-facing chrome. |
| NFR-6 | API keys stay in `.env`; rotate if leaked in chat or screenshots. |

---

## 11. Success metrics (prototype)

Qualitative / demo metrics are enough for this phase:

| Metric | Target |
|--------|--------|
| Time to first path | Learner can get a path for a new skill in one sitting |
| Skill isolation | Switching Guitar ↔ Python never shows the other path |
| Link quality | Opened resources load (no fake `watch?v=` placeholders) |
| Multi-skill | Learner can enroll ≥2 skills and keep separate chats |
| Adaptation | “Too hard” changes remaining items, not completed ones |

Later (if productized): weekly active learners, path completion rate, assessment-to-mastery lift, % of resources opened.

---

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM invents URLs | Broken trust | Resource repair + Tavily + curated list |
| Path bleed across skills | Wrong learning | `strict` active-path lookup by `skill_id` |
| Tavily / Groq quota | Empty or fallback paths | Heuristic catalog path; show honest empty states |
| Email-only auth | Anyone can open a profile if they know the email | Acceptable for prototype; not for production |
| Mastery vs completion confusion | Inflated progress | Separate topic mastery from item status |
| Keys pasted in chat | Secret leak | `.gitignore` `.env`; rotate keys |

---

## 13. Out of scope / later

- Accounts with passwords, OAuth, or JWT
- Postgres / Neo4j / Qdrant / vector memory
- Next.js rewrite
- Collaborative classrooms
- Offline / PWA
- Native mobile
- Monetization and certificates

---

## 14. Release definition (current prototype)

The current build is **done enough to demo** when all of the following are true:

1. Learner can sign in with email and see Kokoro branding (心 + name).
2. Learner can start or switch a skill from the header.
3. Assistant can take a natural-language goal and keep multiple threads.
4. Assessment can set topic mastery for that skill.
5. Learning path is generated for that skill only, with openable resources.
6. Dashboard shows skill cards, streak, and next action.
7. Feedback adapts the remaining path.
8. Semester Mapping and Role Fit still write into the profile.

---

## 15. Open decisions

- Whether to keep ATS Resume in the primary nav or leave it as a hidden utility route.
- How aggressive regeneration should be after “too hard” (swap one item vs rebuild tail).
- Whether to persist Tavily results on the path so regenerate is not required after a key is added.
- Production auth and hosting — explicitly deferred.
