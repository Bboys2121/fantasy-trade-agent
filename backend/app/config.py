"""Loads settings from the .env file at the repo root. Secrets are never printed."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    league_id: int = int(os.getenv("ESPN_LEAGUE_ID") or 0)
    year: int = int(os.getenv("ESPN_YEAR") or 2026)
    # repr=False keeps secrets out of accidental prints/logs of this object.
    espn_s2: str = field(default=os.getenv("ESPN_S2", ""), repr=False)
    swid: str = field(default=os.getenv("ESPN_SWID", ""), repr=False)
    anthropic_api_key: str = field(default=os.getenv("ANTHROPIC_API_KEY", ""), repr=False)
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{REPO_ROOT / 'fantasy.db'}")


settings = Settings()
