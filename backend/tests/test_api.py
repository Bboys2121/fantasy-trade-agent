from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.agent.agent import AgentResult, ToolCall
from app.api import routes
from app.main import app
from tests.test_analysis import TEAM_A, TEAM_B, TEAM_C

ROSTERS = {"A": TEAM_A, "B": TEAM_B, "C": TEAM_C}


@pytest.fixture
def client():
    app.dependency_overrides[routes.get_rosters] = lambda: ROSTERS
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_teams(client):
    r = client.get("/api/teams")
    assert r.status_code == 200
    assert {t["name"] for t in r.json()} == {"A", "B", "C"}


def test_roster_and_needs(client):
    assert len(client.get("/api/teams/A/roster").json()["players"]) == len(TEAM_A)
    assert client.get("/api/teams/A/needs").json()["needs_weakest_first"][0] == "WR"


def test_trades_endpoint_filters_position(client):
    r = client.get("/api/teams/A/trades", params={"position": "WR", "limit": 3})
    cands = r.json()["candidates"]
    assert 0 < len(cands) <= 3
    assert all(c["i_get"]["position"] == "WR" for c in cands)


def test_unknown_team_is_404(client):
    assert client.get("/api/teams/Nope/roster").status_code == 404


def test_evaluate(client):
    r = client.post("/api/evaluate", json={"my_team": "A", "their_team": "B",
                                           "i_give": ["a_rb4"], "i_get": ["b_wr3"]})
    assert r.status_code == 200 and r.json()["mutually_beneficial"] is True


def test_evaluate_unknown_player_is_404(client):
    r = client.post("/api/evaluate", json={"my_team": "A", "their_team": "B",
                                           "i_give": ["ghost"], "i_get": ["b_wr3"]})
    assert r.status_code == 404


def test_agent_needs_api_key(client, monkeypatch):
    monkeypatch.setattr(routes, "settings", replace(routes.settings, anthropic_api_key=""))
    r = client.post("/api/agent", json={"team": "A", "question": "hi"})
    assert r.status_code == 503


def test_agent_returns_answer_and_tool_calls(client, monkeypatch):
    monkeypatch.setattr(routes, "settings", replace(routes.settings, anthropic_api_key="test"))
    fake = AgentResult("Do it.", [ToolCall("get_team_needs", {"team": "A"}, "{}")])
    monkeypatch.setattr(routes, "run_agent", lambda q, team, rosters: fake)
    body = client.post("/api/agent", json={"team": "A", "question": "hi"}).json()
    assert body["answer"] == "Do it." and body["tool_calls"][0]["name"] == "get_team_needs"
