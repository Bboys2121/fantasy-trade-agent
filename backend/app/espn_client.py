"""Thin wrapper around espn_api. Turns a live League into a plain-dict "snapshot".

The snapshot is the only thing the rest of the app sees, so tests can use a saved
JSON snapshot and never touch ESPN.
"""
import json
from pathlib import Path

from app.config import settings


def _owner_name(team) -> str:
    # espn_api versions differ: `owners` (list of dicts) vs `owner` (string).
    owners = getattr(team, "owners", None)
    if owners and isinstance(owners[0], dict):
        o = owners[0]
        return f"{o.get('firstName', '')} {o.get('lastName', '')}".strip()
    return str(getattr(team, "owner", "") or "")


def fetch_snapshot() -> dict:
    from espn_api.football import League  # imported here so tests don't need it

    league = League(
        league_id=settings.league_id,
        year=settings.year,
        espn_s2=settings.espn_s2 or None,
        swid=settings.swid or None,
    )
    teams = []
    for t in league.teams:
        teams.append({
            "espn_team_id": t.team_id,
            "name": t.team_name,
            "owner": _owner_name(t),
            "wins": t.wins,
            "losses": t.losses,
            "roster": [
                {
                    "espn_player_id": p.playerId,
                    "name": p.name,
                    "position": p.position,
                    "pro_team": p.proTeam,
                    "injury_status": getattr(p, "injuryStatus", "ACTIVE"),
                    "total_points": getattr(p, "total_points", 0) or 0,
                    "projected_points": getattr(p, "projected_total_points", 0) or 0,
                    "lineup_slot": p.lineupSlot,  # e.g. "QB", "RB", "BE", "IR"
                }
                for p in t.roster
            ],
        })
    return {"year": settings.year, "teams": teams}


def sanitize(snapshot: dict) -> dict:
    """Replace real owner names so the fixture is safe to commit."""
    clean = json.loads(json.dumps(snapshot))
    for i, team in enumerate(clean["teams"], start=1):
        team["owner"] = f"Owner {i}"
    return clean


def save_fixture(snapshot: dict, path: Path) -> None:
    path.write_text(json.dumps(sanitize(snapshot), indent=2))
