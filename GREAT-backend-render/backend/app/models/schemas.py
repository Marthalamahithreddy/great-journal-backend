# ═══════════════════════════════════════════════════════════════════════════
# app/models/schemas.py
# Pydantic v2 models for all domain objects.
# These drive both API validation (input) and serialization (output).
#
# GREAT-specific fields derived from Author Guidelines v1.0:
#   - article_type is always "Narrative Mini-Review"
#   - literature_window: 2-year rolling window from submission date
#   - required: research_questions, thematic_sections, synthesis_output
#   - citation_style: IEEE only
# ═══════════════════════════════════════════════════════════════════════════

from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


# ── Enums ─────────────────────────────────────────────────────────────────

class ArticleType(str, Enum):
    """GREAT only publishes narrative mini-reviews."""
    NARRATIVE_MINI_REVIEW = "Narrative Mini-Review"


class AccessType(str, Enum):
    OPEN       = "open"        # CC BY 4.0 — default for GREAT
    RESTRICTED = "restricted"


class SubmissionStatus(str, Enum):
    RECEIVED       = "received"
    UNDER_REVIEW   = "under_review"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    ACCEPTED       = "accepted"
    REJECTED       = "rejected"
    PUBLISHED      = "published"


class Pillar(str, Enum):
    """GREAT's four interdisciplinary pillars (Call for Papers)."""
    ENGINEERING_TECH      = "Engineering & Technology"
    MANAGEMENT_ADMIN      = "Management & Administration"
    INNOVATION_ENTREPRENEURSHIP = "Innovation & Entrepreneurship"
    SUSTAINABILITY_POLICY = "Sustainability & Policy"


class SynthesisOutputType(str, Enum):
    """Required output: at least one of these per article (Author Guidelines §3.2)."""
    GAP_ANALYSIS       = "Gap Analysis"
    SOLUTION_FRAMEWORK = "Proposed Solution Framework"
    RQ_ANSWERS         = "Research Question Answers"


# ── Sub-models ────────────────────────────────────────────────────────────

class AuthorInfo(BaseModel):
    name:        str
    affiliation: str
    orcid:       Optional[str] = None
    email:       Optional[EmailStr] = None


class ThematicSection(BaseModel):
    """Represents one thematic section in the article body (min 3 required)."""
    theme_number: int = Field(ge=1, le=10)
    theme_title:  str
    summary:      str    # 200-300 word synthesis narrative


class ResearchQuestion(BaseModel):
    rq_number: int = Field(ge=1)
    question:  str
    answer:    Optional[str] = None   # filled at publication


# ── Core domain models ─────────────────────────────────────────────────────

class ArticleBase(BaseModel):
    title:              str  = Field(max_length=200)   # max 20 words per template
    authors:            List[AuthorInfo]
    abstract:           str  = Field(max_length=2000)  # max 250 words
    keywords:           List[str] = Field(min_length=5, max_length=7)  # 5-7 per guidelines
    pillar:             Pillar
    research_questions: List[ResearchQuestion] = Field(min_length=1)
    thematic_sections:  List[ThematicSection]  = Field(min_length=3)  # min 3 themes
    synthesis_outputs:  List[SynthesisOutputType] = Field(min_length=1)
    doi:                Optional[str] = None
    article_type:       ArticleType = ArticleType.NARRATIVE_MINI_REVIEW
    access:             AccessType  = AccessType.OPEN  # GREAT = open access
    pages:              Optional[str] = None
    # Dates
    literature_window_start: Optional[date] = None  # 2-year rolling window
    literature_window_end:   Optional[date] = None
    received:  Optional[date] = None
    accepted:  Optional[date] = None
    published: Optional[date] = None
    # Metrics (server-side only)
    citations:  int = 0
    views:      int = 0
    downloads:  int = 0


class ArticleCreate(ArticleBase):
    """Used for submission form → creates a Submission, not a published Article."""
    pass


class ArticleOut(ArticleBase):
    """What the API returns. `id` is the MongoDB _id serialized to str."""
    id:       str
    issue_id: Optional[str] = None

    class Config:
        populate_by_name = True


# ── Issue ──────────────────────────────────────────────────────────────────

class IssueBase(BaseModel):
    volume:       int = Field(ge=1)
    issue:        int = Field(ge=1, le=4)
    year:         int = Field(ge=2025)
    title:        str
    date_label:   str          # e.g. "February 2026"
    deadline:     Optional[date] = None

class IssueCreate(IssueBase):
    pass

class IssueOut(IssueBase):
    id:            str
    article_count: int = 0

    class Config:
        populate_by_name = True


# ── Submission ─────────────────────────────────────────────────────────────
# A submission is a manuscript sent through the portal.
# It becomes an Article only when status == "published".

class SubmissionCreate(BaseModel):
    """Exactly matches the GREAT submission form fields."""
    # Title Page fields (Author Guidelines §4)
    title:              str  = Field(max_length=200)
    authors:            List[AuthorInfo]
    word_count:         Optional[int] = None
    table_count:        Optional[int] = None
    figure_count:       Optional[int] = None

    # Abstract (structured, max 250 words)
    abstract_background:        str
    abstract_research_questions:str
    abstract_methods:           str
    abstract_key_findings:      str
    abstract_conclusion_gaps:   str

    keywords:           List[str] = Field(min_length=5, max_length=7)
    pillar:             Pillar
    research_questions: List[ResearchQuestion] = Field(min_length=1)

    # Review design
    databases_searched: List[str]
    literature_start:   date   # must be within 2-year window
    literature_end:     date

    thematic_sections:  List[ThematicSection] = Field(min_length=3)
    synthesis_outputs:  List[SynthesisOutputType] = Field(min_length=1)

    # Declarations (Author Guidelines §8)
    conflicts_of_interest:   str
    ai_tools_used:           Optional[str] = None  # must disclose if used
    corresponding_email:     EmailStr
    target_issue:            Optional[str] = "regular"

    # Checklist (Author Guidelines §6.1) — all must be True
    checklist_page_limit:        bool
    checklist_literature_window: bool
    checklist_summary_tables:    bool
    checklist_abstract_250:      bool
    checklist_rq_stated:         bool
    checklist_gap_or_framework:  bool
    checklist_ieee_citations:    bool
    checklist_docx_format:       bool
    checklist_title_page_complete: bool
    checklist_conflicts_declared:  bool
    checklist_plagiarism_checked:  bool


class SubmissionOut(BaseModel):
    id:            str
    submission_id: str      # e.g. GREAT-2025-XXXXXXXX
    status:        SubmissionStatus
    submitted_at:  datetime
    title:         str
    authors:       List[AuthorInfo]
    corresponding_email: EmailStr
    message:       str = ""

    class Config:
        populate_by_name = True


# ── Stats ──────────────────────────────────────────────────────────────────

class PlatformStats(BaseModel):
    total_articles:          int
    total_submissions:       int
    pending_submissions:     int
    total_issues:            int
    total_authors:           int
    avg_review_days:         int = 49   # midpoint of 6-8 week target
    acceptance_rate:         float
    open_access_percent:     float = 100.0  # GREAT is always OA
    countries_represented:   int
