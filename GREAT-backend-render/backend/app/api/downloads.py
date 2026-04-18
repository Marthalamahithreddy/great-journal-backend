# app/api/downloads.py
# Template/guidelines download links
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

DOWNLOADS = {
    "author_guidelines": {
        "name": "GREAT Author Guidelines v1.0",
        "url":  "/static/GREAT_Author_Guidelines.docx",
        "size": "124 KB",
    },
    "article_template": {
        "name": "GREAT Article Template v1.0",
        "url":  "/static/GREAT_Article_Template.docx",
        "size": "98 KB",
    },
    "call_for_papers": {
        "name": "GREAT Call for Papers 2025/2026",
        "url":  "/static/GREAT_Call_for_Papers.docx",
        "size": "86 KB",
    },
}

@router.get("/downloads")
async def list_downloads():
    return DOWNLOADS
