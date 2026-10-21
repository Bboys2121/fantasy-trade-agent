"""FastAPI app. Run from backend/:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.session import init_db, make_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(make_engine())  # create tables on startup if the DB is new
    yield


app = FastAPI(title="Fantasy Trade Agent", lifespan=lifespan)
app.include_router(router)
