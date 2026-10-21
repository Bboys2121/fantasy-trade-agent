import json
from types import SimpleNamespace as NS

import pytest

from app.agent.agent import MAX_STEPS, run_agent
from app.agent.tools import TOOL_SCHEMAS, LeagueTools, ToolError
from tests.test_analysis import TEAM_A, TEAM_B, TEAM_C

ROSTERS = {"A": TEAM_A, "B": TEAM_B, "C": TEAM_C}


# ---- tools ----------------------------------------------------------------
def test_find_trade_candidates_filters_by_position():
    out = json.loads(LeagueTools(ROSTERS).run(
        "find_trade_candidates", {"my_team": "A", "position": "WR"}))
    assert out["candidates"]
    assert all(c["i_get"]["position"] == "WR" and c["trade_partner"] == "B"
               for c in out["candidates"])


def test_evaluate_trade_matches_manual_math():
    out = json.loads(LeagueTools(ROSTERS).run("evaluate_trade", {
        "my_team": "a", "their_team": "B", "i_give": ["a_rb4"], "i_get": ["b_wr3"]}))
    assert out["my_team"]["gain"] > 0 and out["their_team"]["gain"] > 0
    assert out["mutually_beneficial"] is True


def test_evaluate_unequal_trade_adds_note():
    out = json.loads(LeagueTools(ROSTERS).run("evaluate_trade", {
        "my_team": "A", "their_team": "B", "i_give": ["a_rb4", "a_rb3"], "i_get": ["b_wr3"]}))
    assert "note" in out


def test_team_needs_and_player_details():
    t = LeagueTools(ROSTERS)
    assert json.loads(t.run("get_team_needs", {"team": "A"}))["needs_weakest_first"][0] == "WR"
    details = json.loads(t.run("get_player_details", {"player_name": "A_RB3"}))
    assert details["fantasy_team"] == "A" and details["starting_for_their_fantasy_team"]


def test_bad_names_raise_tool_error():
    t = LeagueTools(ROSTERS)
    with pytest.raises(ToolError):
        t.run("get_team_roster", {"team": "Nope"})
    with pytest.raises(ToolError):
        t.run("get_player_details", {"player_name": "Nobody"})
    with pytest.raises(ToolError):
        t.run("delete_everything", {})


def test_schemas_are_strict_and_complete():
    for s in TOOL_SCHEMAS:
        assert s["input_schema"]["additionalProperties"] is False
        assert set(s["input_schema"]["required"]) <= set(s["input_schema"]["properties"])


# ---- agent loop with a scripted fake client ----------------------------------
def tool_use(name, input, id="t1"):
    return NS(type="tool_use", name=name, input=input, id=id)


def reply(*blocks, stop="tool_use"):
    return NS(content=list(blocks), stop_reason=stop)


class FakeClient:
    """Returns scripted responses and records the messages it was sent."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []
        self.messages = self  # so client.messages.create(...) works

    def create(self, **kwargs):
        self.sent.append([dict(m) for m in kwargs["messages"]])
        return self.responses.pop(0)


def test_loop_runs_tool_then_returns_answer():
    client = FakeClient([
        reply(tool_use("find_trade_candidates", {"my_team": "A", "position": "WR"})),
        reply(NS(type="text", text="Trade a_rb4 for a WR."), stop="end_turn"),
    ])
    seen = []
    result = run_agent("find me a WR", "A", ROSTERS, client=client, on_tool_call=seen.append)

    assert result.answer == "Trade a_rb4 for a WR."
    assert [c.name for c in result.tool_calls] == ["find_trade_candidates"] == [c.name for c in seen]
    # Second request must contain the tool_result, linked to the right tool_use id.
    tool_result = client.sent[1][-1]["content"][0]
    assert tool_result["tool_use_id"] == "t1" and tool_result["is_error"] is False


def test_bad_tool_call_is_reported_back_not_raised():
    client = FakeClient([
        reply(tool_use("get_team_roster", {"team": "Nope"})),
        reply(NS(type="text", text="Sorry."), stop="end_turn"),
    ])
    result = run_agent("hi", "A", ROSTERS, client=client)
    assert result.tool_calls[0].is_error
    assert client.sent[1][-1]["content"][0]["is_error"] is True


def test_missing_argument_is_reported_back():
    client = FakeClient([reply(tool_use("get_team_roster", {})),
                         reply(NS(type="text", text="ok"), stop="end_turn")])
    assert run_agent("hi", "A", ROSTERS, client=client).tool_calls[0].is_error


def test_step_limit_stops_runaway_loop():
    looping = [reply(tool_use("get_team_roster", {"team": "A"})) for _ in range(MAX_STEPS)]
    result = run_agent("hi", "A", ROSTERS, client=FakeClient(looping))
    assert "too many" in result.answer and len(result.tool_calls) == MAX_STEPS
