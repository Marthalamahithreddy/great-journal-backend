# ═══════════════════════════════════════════════════════════════════════════
# app/core/config.py
# All environment-driven settings in one place.
# Set via .env file locally; via Render/Railway env vars in production.
# ═══════════════════════════════════════════════════════════════════════════

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── MongoDB ───────────────────────────────────────────────────────────
    # Free: MongoDB Atlas M0 (512 MB, always free)
    # Format: mongodb+srv://user:pass@cluster.mongodb.net/great_journal
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB:  str = "great_journal"

    # ── Redis (optional caching) ──────────────────────────────────────────
    # Free: Upstash Redis (10 MB free tier, serverless)
    # Format: redis://default:password@hostname:port
    REDIS_URL: str = ""           # empty = Redis disabled, falls back to no-cache

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]   # Lock to your Netlify URL in production

    # ── App ───────────────────────────────────────────────────────────────
    APP_ENV:    str = "development"   # "production" in prod
    SECRET_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
