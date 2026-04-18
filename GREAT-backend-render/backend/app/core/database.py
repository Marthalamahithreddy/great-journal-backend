# ═══════════════════════════════════════════════════════════════════════════
# app/core/database.py
# Async MongoDB via Motor. Single client, single database reference.
# All collections accessed through `get_db()`.
# ═══════════════════════════════════════════════════════════════════════════

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Module-level client — created once at startup
_client: AsyncIOMotorClient | None = None
_db:     AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    """Called at app startup. Creates Motor client + indexes."""
    global _client, _db
    _client = AsyncIOMotorClient(settings.MONGO_URI)
    _db     = _client[settings.MONGO_DB]
    await _ensure_indexes(_db)
    logger.info(f"MongoDB connected: {settings.MONGO_DB}")


async def close_db() -> None:
    """Called at app shutdown. Closes Motor client cleanly."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_db() -> AsyncIOMotorDatabase:
    """Dependency-injectable DB accessor used in all route handlers."""
    if _db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _db


# ── Index Strategy ────────────────────────────────────────────────────────
# Indexes are idempotent — safe to run on every startup.
# Design rationale:
#   articles     : text index for full-text search; compound for filtering
#   submissions  : status + date for editorial queue queries
#   issues       : (volume, issue) unique for deduplication
async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    # Articles — full-text search across title + abstract + keywords
    await db.articles.create_index(
        [("title", "text"), ("abstract", "text"), ("keywords", "text")],
        name="article_fulltext"
    )
    # Articles — compound for type/access filter queries
    await db.articles.create_index(
        [("issue_id", 1), ("type", 1), ("access", 1), ("published", -1)],
        name="article_filter"
    )
    # Articles — citations desc for "most cited" sort
    await db.articles.create_index([("citations", -1)], name="article_citations")

    # Submissions — editorial queue
    await db.submissions.create_index(
        [("status", 1), ("submitted_at", -1)],
        name="submission_queue"
    )

    # Issues — unique volume+issue
    await db.issues.create_index(
        [("volume", 1), ("issue", 1)],
        unique=True, name="issue_unique"
    )

    logger.info("MongoDB indexes ensured")
