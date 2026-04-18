# ═══════════════════════════════════════════════════════════════════════════
# app/api/issues.py  — Issue list + detail
# ═══════════════════════════════════════════════════════════════════════════
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from app.core.database import get_db
from app.core.cache import cache_get, cache_set
from app.models.schemas import IssueOut

router = APIRouter()


def _ser(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/issues", response_model=List[IssueOut])
async def list_issues(db: AsyncIOMotorDatabase = Depends(get_db)):
    cached = await cache_get("issues:all")
    if cached:
        return cached
    docs = await db.issues.find().sort([("year", -1), ("issue", -1)]).to_list(50)
    for d in docs:
        d["article_count"] = await db.articles.count_documents(
            {"issue_id": str(d["_id"]), "status": "published"}
        )
    result = [_ser(d) for d in docs]
    await cache_set("issues:all", result, ttl=120)
    return result


@router.get("/issues/{issue_id}/articles")
async def get_issue_articles(
    issue_id: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    docs = await db.articles.find(
        {"issue_id": issue_id, "status": "published"}
    ).sort([("published", 1)]).to_list(50)
    return [_ser(d) for d in docs]
