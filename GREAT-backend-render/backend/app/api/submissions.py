# ═══════════════════════════════════════════════════════════════════════════
# app/api/submissions.py
# Submission endpoint. Enforces ALL GREAT Author Guidelines rules:
#   - 5-7 keywords
#   - Min 3 thematic sections
#   - Min 1 synthesis output
#   - 2-year literature window
#   - All checklist items must be True
# ═══════════════════════════════════════════════════════════════════════════

import random
import string
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.cache import cache_invalidate_pattern
from app.models.schemas import SubmissionCreate, SubmissionOut, SubmissionStatus

router = APIRouter()


def _generate_submission_id() -> str:
    """GREAT-2025-XXXXXXXX format."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"GREAT-{datetime.now().year}-{suffix}"


def _validate_literature_window(start: date, end: date) -> None:
    """
    Author Guidelines §5.4: all refs must be within 2-year rolling window.
    We validate the declared window is ≤ 2 years and end ≤ today.
    """
    today = date.today()
    two_years_ago = today - timedelta(days=730)

    if end > today:
        raise HTTPException(
            status_code=422,
            detail="literature_end cannot be in the future."
        )
    if start < two_years_ago:
        raise HTTPException(
            status_code=422,
            detail=(
                f"literature_start ({start}) is outside the 2-year rolling window "
                f"(earliest allowed: {two_years_ago}). "
                "GREAT only accepts sources from the immediate past 2 years."
            )
        )
    if (end - start).days > 730:
        raise HTTPException(
            status_code=422,
            detail="Literature window exceeds 2 years."
        )


def _validate_checklist(sub: SubmissionCreate) -> None:
    """Every checklist item must be True. Author Guidelines §6.1."""
    checklist_fields = [
        ("checklist_page_limit",          "Manuscript must be 8–10 pages (incl. references)"),
        ("checklist_literature_window",   "All cited refs must fall within the 2-year window"),
        ("checklist_summary_tables",      "At least one summary table per thematic section required"),
        ("checklist_abstract_250",        "Abstract must be structured and ≤250 words"),
        ("checklist_rq_stated",           "Research question(s) must be explicitly stated"),
        ("checklist_gap_or_framework",    "Gap analysis, framework, or RQ answers required"),
        ("checklist_ieee_citations",      "IEEE citation format must be used throughout"),
        ("checklist_docx_format",         "Manuscript must be submitted as .docx"),
        ("checklist_title_page_complete", "Title page with ORCID iDs and corresponding email required"),
        ("checklist_conflicts_declared",  "Conflicts of interest statement required"),
        ("checklist_plagiarism_checked",  "Plagiarism check (similarity <15%) must be confirmed"),
    ]
    failed = [
        msg for field, msg in checklist_fields
        if not getattr(sub, field, False)
    ]
    if failed:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Submission checklist incomplete",
                "failed_items": failed
            }
        )


# ── POST /submissions ──────────────────────────────────────────────────────
@router.post("/submissions", response_model=SubmissionOut, status_code=201)
async def create_submission(
    payload: SubmissionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # 1. Validate GREAT-specific rules
    _validate_literature_window(payload.literature_start, payload.literature_end)
    _validate_checklist(payload)

    # 2. Build MongoDB document
    sub_id  = _generate_submission_id()
    now     = datetime.utcnow()
    doc = payload.model_dump()
    doc.update({
        "submission_id": sub_id,
        "status":        SubmissionStatus.RECEIVED,
        "submitted_at":  now,
        "updated_at":    now,
    })

    # 3. Persist
    result = await db.submissions.insert_one(doc)

    # 4. Invalidate stats cache so counts update immediately
    await cache_invalidate_pattern("stats:*")

    return SubmissionOut(
        id            = str(result.inserted_id),
        submission_id = sub_id,
        status        = SubmissionStatus.RECEIVED,
        submitted_at  = now,
        title         = payload.title,
        authors       = payload.authors,
        corresponding_email = payload.corresponding_email,
        message = (
            f"Manuscript received. Submission ID: {sub_id}. "
            "You will receive a decision within 6–8 weeks via double-blind peer review."
        )
    )


# ── GET /submissions/{sub_id} — tracking endpoint ─────────────────────────
@router.get("/submissions/{submission_id}")
async def track_submission(
    submission_id: str,
    email: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Authors can check their submission status using ID + email."""
    doc = await db.submissions.find_one({"submission_id": submission_id})
    if not doc or doc.get("corresponding_email") != email:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "submission_id": submission_id,
        "title":         doc["title"],
        "status":        doc["status"],
        "submitted_at":  doc["submitted_at"],
        "updated_at":    doc.get("updated_at"),
    }
