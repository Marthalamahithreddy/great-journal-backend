# ═══════════════════════════════════════════════════════════════════════════
# app/api/articles.py
# Article endpoints: list, search (full-text), single detail, view/download tracking.
# All responses are cached in Redis where possible.
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional

from app.core.database import get_db
from app.core.cache import cache_get, cache_set
from app.models.schemas import ArticleOut

router = APIRouter()


def _serialize(doc: dict) -> dict:
    """Convert MongoDB _id ObjectId → string 'id' for JSON output."""
    doc["id"] = str(doc.pop("_id"))
    if doc.get("issue_id"):
        doc["issue_id"] = str(doc["issue_id"])
    return doc


# ── GET /articles — list + search ─────────────────────────────────────────
@router.get("/articles", response_model=List[ArticleOut])
async def list_articles(
    q:       Optional[str] = Query(None, description="Full-text search query"),
    pillar:  Optional[str] = Query(None, description="Filter by GREAT pillar"),
    access:  Optional[str] = Query(None, description="open | restricted"),
    sort_by: str           = Query("published", description="published|citations|views"),
    page:    int           = Query(1, ge=1),
    limit:   int           = Query(20, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # Build cache key from all query params
    cache_key = f"articles:{q}:{pillar}:{access}:{sort_by}:{page}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Build MongoDB filter
    filt: dict = {"status": "published"}
    if pillar:
        filt["pillar"] = pillar
    if access:
        filt["access"] = access

    # Full-text search uses the text index; otherwise sort by field
    skip = (page - 1) * limit
    sort_field = {"citations": -1, "views": -1}.get(sort_by, {"published": -1})

    if q:
        filt["$text"] = {"$search": q}
        cursor = db.articles.find(filt, {"score": {"$meta": "textScore"}})
        cursor = cursor.sort([("score", {"$meta": "textScore"})])
    else:
        cursor = db.articles.find(filt).sort(list(sort_field.items()))

    docs = await cursor.skip(skip).limit(limit).to_list(length=limit)
    result = [_serialize(d) for d in docs]

    await cache_set(cache_key, result, ttl=30)
    return result


# ── GET /articles/{id} — single article detail ────────────────────────────
@router.get("/articles/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        oid = ObjectId(article_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    doc = await db.articles.find_one({"_id": oid, "status": "published"})
    if not doc:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment view counter (fire-and-forget, non-blocking)
    await db.articles.update_one({"_id": oid}, {"$inc": {"views": 1}})
    doc["views"] += 1

    return _serialize(doc)


# ── POST /articles/{id}/track-download — increment download counter ────────
@router.post("/articles/{article_id}/track-download")
async def track_download(
    article_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    try:
        oid = ObjectId(article_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    result = await db.articles.update_one({"_id": oid}, {"$inc": {"downloads": 1}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"ok": True}
