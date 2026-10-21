"""FastAPI app. Run from backend/:  uvicorn app.main:app --reload"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import REPO_ROOT
from app.db.session import init_db, make_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(make_engine())  # create tables on startup if the DB is new
    yield


app = FastAPI(title="Fantasy Trade Agent", lifespan=lifespan)
app.include_router(router)

# If the React app has been built (`npm run build`, or inside the Docker image), serve it from
# the same server so production is a single process. Mounted AFTER the API router so /api wins.
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"))
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="web")
