"""REST endpoints. Thin layer: each route calls the same LeagueTools the agent uses."""
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agent.agent import run_agent
from app.agent.tools import LeagueTools, ToolError
from app.analysis.roster_scoring import lineup_points, load_rosters
from app.config import settings
from app.db.models import Team
from app.db.session import get_session, make_engine

router = APIRouter(prefix="/api")


def get_rosters() -> dict:
    """Load rosters from SQLite for this request. Tests override this dependency."""
    with get_session(make_engine()) as session:
        return load_rosters(session)


def get_tools(rosters: dict = Depends(get_rosters)) -> LeagueTools:
    return LeagueTools(rosters)


def _call(fn, *args, **kwargs):
    """Turn the tools' 'unknown team/player' errors into HTTP 404s."""
    try:
        return fn(*args, **kwargs)
    except ToolError as e:
        raise HTTPException(status_code=404, detail=str(e))


class TradeRequest(BaseModel):
    my_team: str
    their_team: str
    i_give: list[str]
    i_get: list[str]


class AgentRequest(BaseModel):
    team: str
    question: str


@router.get("/teams")
def list_teams(tools: LeagueTools = Depends(get_tools)):
    return [{"name": name, "lineup_projected_points": round(lineup_points(players), 1)}
            for name, players in tools.rosters.items()]


@router.get("/teams/{team}/roster")
def roster(team: str, tools: LeagueTools = Depends(get_tools)):
    return _call(tools.get_team_roster, team)


@router.get("/teams/{team}/needs")
def team_needs(team: str, tools: LeagueTools = Depends(get_tools)):
    return _call(tools.get_team_needs, team)


@router.get("/teams/{team}/trades")
def trade_candidates(team: str, position: str | None = None, limit: int = 10,
                     tools: LeagueTools = Depends(get_tools)):
    """Deterministic candidates only (no LLM, free and instant)."""
    return _call(tools.find_trade_candidates, team, position, limit)


@router.post("/evaluate")
def evaluate(req: TradeRequest, tools: LeagueTools = Depends(get_tools)):
    return _call(tools.evaluate_trade, req.my_team, req.their_team, req.i_give, req.i_get)


@router.post("/agent")
def ask_agent(req: AgentRequest, rosters: dict = Depends(get_rosters)):
    """Run the Claude agent. Returns the answer plus every tool call it made."""
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY is not set on the server.")
    if req.team not in rosters:
        raise HTTPException(status_code=404, detail=f"Unknown team '{req.team}'.")
    result = run_agent(req.question, req.team, rosters)
    return {"answer": result.answer, "tool_calls": [asdict(c) for c in result.tool_calls]}
