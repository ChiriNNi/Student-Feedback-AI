import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine, wait_for_db
from .routers import auth

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
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(424242)"))
    if settings.seed_demo_data:
        from .seed import seed
        with SessionLocal() as db:
            seed(db)
    log.info("Pulse API ready")
    yield


app = FastAPI(
    title="Pulse — Login API",
    version="1.0.0",
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


@app.get("/api/health", tags=["system"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
