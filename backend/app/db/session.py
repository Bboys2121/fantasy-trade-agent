from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base


def make_engine(url: str | None = None):
    return create_engine(url or settings.database_url)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def get_session(engine=None) -> Session:
    return sessionmaker(bind=engine or make_engine())()
