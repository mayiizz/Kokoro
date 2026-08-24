from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db import init_db
from app.routes import assessment, assistant, catalog, dashboard, learner, path, resume, role_fit, roadmap, semester, skills

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Kokoro Backend", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
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
async def root():
    return {"message": "Kokoro Backend Running"}
