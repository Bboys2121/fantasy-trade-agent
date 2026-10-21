import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.models import Player, RosterSlot, Team
from app.db.session import get_session, init_db, make_engine
from app.espn_client import sanitize
from app.sync import load_snapshot, summarize

FIXTURE = Path(__file__).parent / "fixtures" / "league_snapshot.json"


@pytest.fixture
def snapshot():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def session():
    engine = make_engine("sqlite://")  # in-memory, fresh per test
    init_db(engine)
    with get_session(engine) as s:
        yield s


def test_load_snapshot_creates_teams_and_rosters(session, snapshot):
    load_snapshot(session, snapshot)
    assert session.scalar(select(func.count(Team.id))) == len(snapshot["teams"])
    expected = sum(len(t["roster"]) for t in snapshot["teams"])
    assert session.scalar(select(func.count(RosterSlot.id))) == expected
    assert session.scalar(select(func.count(Player.id))) == expected


def test_sync_is_idempotent(session, snapshot):
    load_snapshot(session, snapshot)
    load_snapshot(session, snapshot)  # second sync must not duplicate rows
    assert session.scalar(select(func.count(Team.id))) == len(snapshot["teams"])
    assert session.scalar(select(func.count(RosterSlot.id))) == sum(
        len(t["roster"]) for t in snapshot["teams"]
    )


def test_summary_lists_every_team(session, snapshot):
    load_snapshot(session, snapshot)
    text = summarize(session)
    for t in snapshot["teams"]:
        assert t["name"] in text


def test_sanitize_hides_owner_names(snapshot):
    snapshot["teams"][0]["owner"] = "Real Person"
    assert "Real Person" not in json.dumps(sanitize(snapshot))
