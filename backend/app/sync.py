"""Pull the league from ESPN into SQLite.

Usage:
    python -m app.sync                      # live ESPN -> DB, prints summary
    python -m app.sync --save-fixture PATH  # also write a sanitized snapshot
    python -m app.sync --from-file PATH     # load a saved snapshot instead of ESPN
"""
import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Player, RosterSlot, Team
from app.db.session import get_session, init_db, make_engine


def load_snapshot(session: Session, snapshot: dict) -> None:
    """Replace teams/rosters with the snapshot. Players are upserted by ESPN id."""
    session.query(RosterSlot).delete()
    session.query(Team).delete()
    players = {p.espn_player_id: p for p in session.scalars(select(Player))}

    for t in snapshot["teams"]:
        team = Team(espn_team_id=t["espn_team_id"], name=t["name"], owner=t["owner"],
                    wins=t["wins"], losses=t["losses"])
        session.add(team)
        for p in t["roster"]:
            player = players.get(p["espn_player_id"])
            if player is None:
                player = Player(espn_player_id=p["espn_player_id"])
                players[p["espn_player_id"]] = player
                session.add(player)
            player.name = p["name"]
            player.position = p["position"]
            player.pro_team = p["pro_team"]
            player.injury_status = p["injury_status"]
            player.total_points = p["total_points"]
            player.projected_points = p["projected_points"]
            team.roster.append(RosterSlot(player=player, lineup_slot=p["lineup_slot"]))
    session.commit()


def summarize(session: Session) -> str:
    lines = []
    for team in session.scalars(select(Team).order_by(Team.espn_team_id)):
        lines.append(f"{team.name} ({team.owner}) {team.wins}-{team.losses}")
        for slot in team.roster:
            p = slot.player
            flag = "" if p.injury_status in ("ACTIVE", "NORMAL") else f" [{p.injury_status}]"
            lines.append(f"  {slot.lineup_slot:<4} {p.position:<4} {p.name} "
                         f"({p.pro_team}) proj {p.projected_points:.1f}{flag}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-fixture", type=Path)
    parser.add_argument("--from-file", type=Path)
    args = parser.parse_args()

    if args.from_file:
        snapshot = json.loads(args.from_file.read_text())
    else:
        from app.espn_client import fetch_snapshot
        snapshot = fetch_snapshot()
    if args.save_fixture:
        from app.espn_client import save_fixture
        save_fixture(snapshot, args.save_fixture)
        print(f"Saved sanitized fixture to {args.save_fixture}")

    engine = make_engine()
    init_db(engine)
    with get_session(engine) as session:
        load_snapshot(session, snapshot)
        print(summarize(session))


if __name__ == "__main__":
    main()
