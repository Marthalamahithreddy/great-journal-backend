# ═══════════════════════════════════════════════════════════════════════════
# GREAT Journal — FastAPI Backend  (main.py)
# Global Review of Engineering, Administration & Transformation
#
# Entry point. Mounts all routers, configures CORS, lifespan events.
# ═══════════════════════════════════════════════════════════════════════════

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_db, close_db
from app.api import articles, submissions, issues, stats, downloads


# ── Lifespan: connect/disconnect MongoDB on startup/shutdown ──────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


# ── App instance ──────────────────────────────────────────────────────────
app = FastAPI(
    title="GREAT Journal API",
    description="Global Review of Engineering, Administration & Transformation",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow frontend on any origin in dev; lock down in prod ─────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(stats.router,       prefix="/api/v1", tags=["Stats"])
app.include_router(issues.router,      prefix="/api/v1", tags=["Issues"])
app.include_router(articles.router,    prefix="/api/v1", tags=["Articles"])
app.include_router(submissions.router, prefix="/api/v1", tags=["Submissions"])
app.include_router(downloads.router,   prefix="/api/v1", tags=["Downloads"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "journal": "GREAT Journal", "version": "1.0.0"}
