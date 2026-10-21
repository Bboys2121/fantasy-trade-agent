"""Talks to the MCP server through a real in-memory MCP client session (full protocol, no subprocess)."""
import asyncio
import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from app.agent.tools import TOOL_NAMES, LeagueTools
from mcp_server import server
from tests.test_analysis import TEAM_A, TEAM_B, TEAM_C


@pytest.fixture(autouse=True)
def fake_league(monkeypatch):
    tools = LeagueTools({"A": TEAM_A, "B": TEAM_B, "C": TEAM_C})
    monkeypatch.setattr(server, "_tools", lambda: tools)  # skip the database


def with_client(coro_fn):
    async def run():
        async with create_connected_server_and_client_session(server.mcp._mcp_server) as client:
            return await coro_fn(client)
    return asyncio.run(run())


def test_server_lists_all_agent_tools_with_schemas():
    tools = with_client(lambda c: c.list_tools()).tools
    assert {t.name for t in tools} == TOOL_NAMES
    find = next(t for t in tools if t.name == "find_trade_candidates")
    assert find.inputSchema["required"] == ["my_team"]
    assert "BOTH" in find.description  # description reused from the agent's tool schema


def test_call_tool_returns_json_result():
    result = with_client(lambda c: c.call_tool(
        "evaluate_trade",
        {"my_team": "A", "their_team": "B", "i_give": ["a_rb4"], "i_get": ["b_wr3"]}))
    assert not result.isError
    assert json.loads(result.content[0].text)["mutually_beneficial"] is True


def test_bad_input_comes_back_as_error_result():
    result = with_client(lambda c: c.call_tool("get_team_roster", {"team": "Nope"}))
    assert result.isError
    assert "Unknown team" in result.content[0].text
