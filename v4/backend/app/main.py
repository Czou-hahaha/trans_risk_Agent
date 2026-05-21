"""V4 AI Risk Investigation Workspace — FastAPI entrypoint."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_V4_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_V4_ROOT / ".env")

_ENGINE = _V4_ROOT / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from app.api import investigation, investigations, reports  # noqa: E402
from app.config import settings  # noqa: E402
from app.db.session import init_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("Investigation database initialized")
    yield


app = FastAPI(
    title="AI Investigation Console",
    version="4.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.backend_cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investigations.router)
app.include_router(investigation.router)
app.include_router(reports.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "4.0.0"}
