"""MCP server: exposes the same five league tools the built-in agent uses.

Any MCP client (Claude Desktop, Claude Code, another agent) can connect and call them.
Transport is stdio: the client launches this script and talks over stdin/stdout, so this
file must NEVER print() anything -- stray output would corrupt the protocol stream.

Run directly:  python mcp_server/server.py
"""
from mcp.server.fastmcp import FastMCP

from app.agent.tools import TOOL_SCHEMAS, LeagueTools
from app.analysis.roster_scoring import load_rosters
from app.db.session import get_session, make_engine

mcp = FastMCP("fantasy-trade-agent")

# One source of truth for tool descriptions: reuse the ones the built-in agent sees.
DESC = {s["name"]: s["description"] for s in TOOL_SCHEMAS}


def _tools() -> LeagueTools:
    """Fresh rosters from SQLite on every call, so a new `python -m app.sync` shows up
    immediately without restarting the server."""
    with get_session(make_engine()) as session:
        return LeagueTools(load_rosters(session))


# FastMCP builds each tool's JSON schema from the type hints below.
# A ToolError (unknown team/player) is raised as-is; FastMCP reports it to the client as an
# error result, which the calling model can read and retry -- same as in our own agent.
@mcp.tool(description=DESC["get_team_roster"])
def get_team_roster(team: str) -> dict:
    return _tools().get_team_roster(team)


@mcp.tool(description=DESC["get_player_details"])
def get_player_details(player_name: str) -> dict:
    return _tools().get_player_details(player_name)


@mcp.tool(description=DESC["get_team_needs"])
def get_team_needs(team: str) -> dict:
    return _tools().get_team_needs(team)


@mcp.tool(description=DESC["find_trade_candidates"])
def find_trade_candidates(my_team: str, position: str | None = None, limit: int = 5) -> dict:
    return _tools().find_trade_candidates(my_team, position, limit)


@mcp.tool(description=DESC["evaluate_trade"])
def evaluate_trade(my_team: str, their_team: str, i_give: list[str], i_get: list[str]) -> dict:
    return _tools().evaluate_trade(my_team, their_team, i_give, i_get)


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
