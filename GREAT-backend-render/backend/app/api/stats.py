# app/api/stats.py
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.cache import cache_get, cache_set
from app.models.schemas import PlatformStats

router = APIRouter()

@router.get("/stats", response_model=PlatformStats)
async def get_stats(db: AsyncIOMotorDatabase = Depends(get_db)):
    cached = await cache_get("stats:platform")
    if cached:
        return PlatformStats(**cached)

    total_articles    = await db.articles.count_documents({"status": "published"})
    total_submissions = await db.submissions.count_documents({})
    pending           = await db.submissions.count_documents(
        {"status": {"$in": ["received", "under_review", "minor_revision", "major_revision"]}}
    )
    total_issues = await db.issues.count_documents({})
    accepted = await db.submissions.count_documents(
        {"status": {"$in": ["accepted", "published"]}}
    )
    rate = round((accepted / total_submissions * 100), 1) if total_submissions else 0.0

    # Count unique authors across all published articles
    pipeline = [
        {"$match": {"status": "published"}},
        {"$unwind": "$authors"},
        {"$group": {"_id": "$authors.name"}},
        {"$count": "total"}
    ]
    agg = await db.articles.aggregate(pipeline).to_list(1)
    total_authors = agg[0]["total"] if agg else 0

    stats = PlatformStats(
        total_articles=total_articles,
        total_submissions=total_submissions,
        pending_submissions=pending,
        total_issues=total_issues,
        total_authors=total_authors,
        acceptance_rate=rate,
        countries_represented=43,  # update via admin panel later
    )
    await cache_set("stats:platform", stats.model_dump(), ttl=60)
    return stats
