"""Functions the agent can call. All the real math lives in app.analysis; these are thin
wrappers that look things up by name and return JSON-friendly dicts.
"""
import json

from app.analysis.roster_scoring import (
    RosterPlayer,
    best_lineup,
    lineup_points,
    needs,
    rate_team,
    replacement_levels,
    surpluses,
)
from app.analysis.trade_finder import find_trades


class ToolError(Exception):
    """Bad input from the model (unknown team/player...). Sent back so it can retry."""


def player_dict(p: RosterPlayer) -> dict:
    return {"name": p.name, "position": p.position, "nfl_team": p.pro_team,
            "projected_points": p.projected_points, "injury_status": p.injury_status}


class LeagueTools:
    def __init__(self, rosters: dict[str, list[RosterPlayer]]):
        self.rosters = rosters
        self.replacement = replacement_levels(rosters)

    # ---- lookups -------------------------------------------------------------
    def _team(self, name: str) -> str:
        for team in self.rosters:
            if team.lower() == name.strip().lower():
                return team
        raise ToolError(f"Unknown team '{name}'. Teams: {', '.join(self.rosters)}")

    def _player(self, team: str, name: str) -> RosterPlayer:
        for p in self.rosters[team]:
            if p.name.lower() == name.strip().lower():
                return p
        raise ToolError(f"'{name}' is not on {team}. Roster: "
                        f"{', '.join(p.name for p in self.rosters[team])}")

    # ---- tools ---------------------------------------------------------------
    def get_team_roster(self, team: str) -> dict:
        team = self._team(team)
        starters = best_lineup(self.rosters[team])
        return {"team": team,
                "lineup_projected_points": round(lineup_points(self.rosters[team]), 1),
                "players": [{**player_dict(p), "starting": p in starters}
                            for p in self.rosters[team]]}

    def get_player_details(self, player_name: str) -> dict:
        for team, roster in self.rosters.items():
            for p in roster:
                if p.name.lower() == player_name.strip().lower():
                    return {**player_dict(p), "fantasy_team": team,
                            "season_points_so_far": p.total_points,
                            "starting_for_their_fantasy_team": p in best_lineup(roster),
                            "value_over_replacement": round(
                                p.points - self.replacement.get(p.position, 0.0), 1),
                            "data_limits": "No game logs, schedule or news available."}
        raise ToolError(f"No player named '{player_name}' on any roster.")

    def get_team_needs(self, team: str) -> dict:
        team = self._team(team)
        ratings = rate_team(self.rosters[team], self.replacement)
        return {"team": team,
                "needs_weakest_first": needs(ratings),
                "surplus_positions": surpluses(ratings),
                "by_position": {pos: {"starter_value_over_replacement": round(r.starter_vor, 1),
                                      "bench_value_over_replacement": round(r.bench_vor, 1)}
                                for pos, r in ratings.items()}}

    def find_trade_candidates(self, my_team: str, position: str | None = None,
                              limit: int = 5) -> dict:
        """1-for-1 trades where both teams improve; optionally only those that bring in `position`."""
        my_team = self._team(my_team)
        trades = find_trades(self.rosters, my_team, limit=10_000)
        if position:
            trades = [t for t in trades if t.get.position == position.upper()]
        return {"candidates": [
            {"trade_partner": t.their_team, "i_give": player_dict(t.give), "i_get": player_dict(t.get),
             "my_lineup_gain": round(t.my_gain, 1), "their_lineup_gain": round(t.their_gain, 1)}
            for t in trades[:limit]]}

    def evaluate_trade(self, my_team: str, their_team: str,
                       i_give: list[str], i_get: list[str]) -> dict:
        """Score any N-for-M trade by how each team's best-lineup points change."""
        my_team, their_team = self._team(my_team), self._team(their_team)
        give = [self._player(my_team, n) for n in i_give]
        get = [self._player(their_team, n) for n in i_get]
        mine, theirs = self.rosters[my_team], self.rosters[their_team]
        my_after = [p for p in mine if p not in give] + get
        their_after = [p for p in theirs if p not in get] + give
        my_gain = lineup_points(my_after) - lineup_points(mine)
        their_gain = lineup_points(their_after) - lineup_points(theirs)
        result = {
            "my_team": {"lineup_before": round(lineup_points(mine), 1),
                        "lineup_after": round(lineup_points(my_after), 1),
                        "gain": round(my_gain, 1)},
            "their_team": {"lineup_before": round(lineup_points(theirs), 1),
                           "lineup_after": round(lineup_points(their_after), 1),
                           "gain": round(their_gain, 1)},
            "mutually_beneficial": my_gain > 0 and their_gain > 0,
            "players_involved": [player_dict(p) for p in give + get],
        }
        if len(give) != len(get):
            result["note"] = "Unequal trade: someone must drop players to fit roster limits."
        return result

    # ---- dispatch ------------------------------------------------------------
    def run(self, name: str, args: dict) -> str:
        if name not in TOOL_NAMES:
            raise ToolError(f"Unknown tool '{name}'.")
        return json.dumps(getattr(self, name)(**args))


def _schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"name": name, "description": description,
            "input_schema": {"type": "object", "properties": properties,
                             "required": required, "additionalProperties": False}}


_TEAM = {"type": "string", "description": "Fantasy team name exactly as listed in the league."}

TOOL_SCHEMAS = [
    _schema("get_team_roster",
            "List a fantasy team's players with position, projection, injury status and whether "
            "each is in the best starting lineup.", {"team": _TEAM}, ["team"]),
    _schema("get_player_details",
            "Look up one player by full name: projection, season points so far, injury status, "
            "value over replacement, and which fantasy team owns them.",
            {"player_name": {"type": "string"}}, ["player_name"]),
    _schema("get_team_needs",
            "Which positions a team is weakest at and where it has surplus bench talent.",
            {"team": _TEAM}, ["team"]),
    _schema("find_trade_candidates",
            "Search all 1-for-1 trades where BOTH teams' best lineups improve, ranked best-first. "
            "Optionally filter to trades that bring back a given position (QB/RB/WR/TE).",
            {"my_team": _TEAM,
             "position": {"type": "string", "enum": ["QB", "RB", "WR", "TE"]},
             "limit": {"type": "integer", "description": "Max results, default 5."}},
            ["my_team"]),
    _schema("evaluate_trade",
            "Score a specific trade (any number of players per side) by the change in each team's "
            "projected best-lineup points.",
            {"my_team": _TEAM, "their_team": _TEAM,
             "i_give": {"type": "array", "items": {"type": "string"},
                        "description": "Names of players on my_team that I send."},
             "i_get": {"type": "array", "items": {"type": "string"},
                       "description": "Names of players on their_team that I receive."}},
            ["my_team", "their_team", "i_give", "i_get"]),
]
TOOL_NAMES = {s["name"] for s in TOOL_SCHEMAS}
