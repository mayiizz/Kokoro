# Kokoro

Kokoro is an AI-powered personalized learning-path recommender. Learners describe a goal, the app builds a stored profile, and a catalog-backed engine recommends a sequenced roadmap of courses, projects, and assessments — with explanations, progress tracking, and feedback-driven adaptation.

Semester Mapping and Role Fit still exist as **inputs** that write skills and gaps into the learner profile. ATS Resume remains available at `/home/resume`.

## Features

- **Assistant** — Natural-language goals, profile updates, and Q&A about why items were recommended
- **Learner profile** — Interests, experience, completed courses, skills, and objectives persisted in SQLite
- **Recommendation engine** — Ranks real catalog resources (not hallucinated courses)
- **Learning path** — Prerequisites, milestones, assessments, and per-item explanations
- **Dashboard** — Live progress, skill chips, milestones, and next recommended action
- **Feedback loop** — Mark complete, too hard, or not relevant to regenerate remaining steps
- **Semester Mapping** — Import syllabus skills into the profile
- **Role Fit** — Save target role and skill gaps for path generation

## Project Structure

```
acadbridge/
├── src/                 # React frontend (Vite + TypeScript)
│   ├── context/         # Learner session (localStorage + API)
│   ├── lib/api.ts       # Backend client
│   └── pages/           # Dashboard, Assistant, Path, Profile, ...
├── backend/
│   ├── app/
│   │   ├── data/catalog.json
│   │   ├── models.py    # SQLite models
│   │   ├── routes/
│   │   ├── services/
│   │   └── core/        # Groq client
│   └── requirements.txt
└── package.json
```

## Prerequisites

- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (v3.10+)
- A [Groq API key](https://console.groq.com/) for live AI (path ranking, chat). Without a valid key, path generation falls back to a catalog heuristic.

## Getting Started

### Frontend

```bash
npm install
npm run dev
```

Frontend: **http://localhost:8080**

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Set `GROQ_API_KEY` in `backend/.env`, then:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API: **http://localhost:8000** · Docs: **http://localhost:8000/docs**

Sign in with an email (no password). That email creates or loads a persisted learner.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/learner/login` | Create or load a learner by email |
| `GET/PUT /api/learner/{id}` | Read or update profile |
| `POST /api/learner/{id}/from-semester` | Merge syllabus skills |
| `POST /api/learner/{id}/from-role-fit` | Save role + gaps |
| `GET /api/catalog/` | List learning resources |
| `POST /api/path/generate` | Build a catalog-backed path |
| `GET /api/path/{learner_id}` | Active path |
| `PATCH /api/path/items/{id}` | Complete / skip / feedback |
| `POST /api/path/adapt` | Regenerate remaining items |
| `GET /api/dashboard/{learner_id}` | Progress stats |
| `POST /api/assistant/chat` | Conversational assistant |
| `POST /api/semester/analyze` | Syllabus → skills |
| `POST /api/role-fit/analyze` | Role-fit analysis |
| `POST /api/resume/generate` | ATS resume PDF |

## Tech Stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui

**Backend:** FastAPI, SQLAlchemy/SQLite, Groq AI, Pydantic

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start frontend dev server |
| `npm run build` | Production build |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm run test` | Run frontend tests |
| `python backend/tests/test_wiring.py` | Run backend wiring tests |

## License

MIT
