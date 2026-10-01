import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class Settings:
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://pulse:pulse@db:5432/pulse")
    jwt_secret = os.getenv("JWT_SECRET", "change-me-in-production")
    jwt_hours = _int("JWT_HOURS", 8)
    jwt_remember_hours = _int("JWT_REMEMBER_HOURS", 24 * 7)

    max_login_attempts = _int("MAX_LOGIN_ATTEMPTS", 5)
    lock_seconds = _int("LOCK_SECONDS", 60)

    # Alert when the share of negative feedback grows by this many percentage points
    alert_threshold_pp = _int("ALERT_THRESHOLD_PP", 12)
    alert_min_feedback = _int("ALERT_MIN_FEEDBACK", 8)

    seed_demo_data = os.getenv("SEED_DEMO_DATA", "true").lower() in ("1", "true", "yes")
    demo_password = os.getenv("DEMO_PASSWORD", "Pulse#2026")

    # Optional: LLM summaries via the Claude API. Empty key = local summarizer only.
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    llm_model = os.getenv("LLM_MODEL", "claude-opus-5")

    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8080").split(",") if o.strip()]


settings = Settings()
