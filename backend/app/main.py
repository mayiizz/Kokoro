import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db import init_db
from app.routes import assessment, assistant, catalog, dashboard, learner, path, resume, role_fit, roadmap, semester, skills

load_dotenv()


def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    extra = os.getenv("FRONTEND_ORIGIN", "")
    origins.extend(part.strip() for part in extra.split(",") if part.strip())
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        origins.append(f"https://{vercel_url.removeprefix('https://')}")
    prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    if prod:
        origins.append(f"https://{prod.removeprefix('https://')}")
    return list(dict.fromkeys(origins))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Kokoro Backend", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(semester.router, prefix="/api/semester", tags=["Semester Analysis"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume Generation"])
app.include_router(role_fit.router, prefix="/api/role-fit", tags=["Role Fit"])
app.include_router(roadmap.router, prefix="/api/roadmap", tags=["Roadmap"])
app.include_router(learner.router, prefix="/api/learner", tags=["Learner"])
app.include_router(catalog.router, prefix="/api/catalog", tags=["Catalog"])
app.include_router(path.router, prefix="/api/path", tags=["Learning Path"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["Assistant"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(assessment.router, prefix="/api/assessment", tags=["Assessment"])
app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])


@app.get("/")
@app.get("/api")
async def root():
    return {"message": "Kokoro Backend Running"}
