// Typed wrappers around the FastAPI endpoints. Types mirror the JSON the backend returns.

export interface Player {
  name: string;
  position: string;
  nfl_team: string;
  projected_points: number;
  injury_status: string;
}
export interface RosterPlayer extends Player {
  starting: boolean;
}
export interface TeamSummary {
  name: string;
  lineup_projected_points: number;
}
export interface Roster {
  team: string;
  lineup_projected_points: number;
  players: RosterPlayer[];
}
export interface Needs {
  team: string;
  needs_weakest_first: string[];
  surplus_positions: string[];
}
export interface TradeCandidate {
  trade_partner: string;
  i_give: Player;
  i_get: Player;
  my_lineup_gain: number;
  their_lineup_gain: number;
}
export interface TradeEvaluation {
  my_team: { lineup_before: number; lineup_after: number; gain: number };
  their_team: { lineup_before: number; lineup_after: number; gain: number };
  mutually_beneficial: boolean;
  note?: string;
}
export interface ToolCall {
  name: string;
  input: Record<string, unknown>;
  output: string;
  is_error: boolean;
}
export interface AgentResponse {
  answer: string;
  tool_calls: ToolCall[];
}

async function request<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => null))?.detail;
    throw new Error(detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

const enc = encodeURIComponent;

export const api = {
  teams: () => request<TeamSummary[]>("/teams"),
  roster: (team: string) => request<Roster>(`/teams/${enc(team)}/roster`),
  needs: (team: string) => request<Needs>(`/teams/${enc(team)}/needs`),
  trades: (team: string, position?: string) =>
    request<{ candidates: TradeCandidate[] }>(
      `/teams/${enc(team)}/trades?limit=10${position ? `&position=${position}` : ""}`,
    ),
  evaluate: (myTeam: string, theirTeam: string, give: string[], get: string[]) =>
    request<TradeEvaluation>("/evaluate", {
      my_team: myTeam, their_team: theirTeam, i_give: give, i_get: get,
    }),
  agent: (team: string, question: string) =>
    request<AgentResponse>("/agent", { team, question }),
};
