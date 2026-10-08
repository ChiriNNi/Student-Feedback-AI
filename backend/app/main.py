import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine, wait_for_db
from .routers import admin, auth, evaluations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pulse")


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    # A PostgreSQL advisory lock makes schema creation + seeding safe with several workers
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_lock(424242)"))
        try:
            Base.metadata.create_all(conn)
            # create_all() never alters existing tables, so columns added after the
            # first deploy are applied here (idempotent on every start).
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_reason TEXT"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_at TIMESTAMPTZ"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS ratings JSON"))
            # Receipts used to have a serial id, which would let the n-th receipt be paired
            # with the n-th feedback row; the (user, survey, target) key replaces it.
            conn.execute(text("""
                DO $$ BEGIN
                  IF EXISTS (SELECT 1 FROM information_schema.columns
                             WHERE table_name = 'submission_receipts' AND column_name = 'id') THEN
                    ALTER TABLE submission_receipts DROP COLUMN id;
                    ALTER TABLE submission_receipts ADD PRIMARY KEY (user_id, survey_id, target_key);
                  END IF;
                END $$;"""))
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(424242)"))
    if settings.seed_demo_data:
        from .seed import seed
        with SessionLocal() as db:
            seed(db)
    log.info("Pulse API ready")
    yield


app = FastAPI(
    title="Pulse API",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(evaluations.router)


@app.get("/api/health", tags=["system"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
