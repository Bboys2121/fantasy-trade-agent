import { useEffect, useState } from "react";
import { api, TeamSummary } from "./api";
import RosterPanel from "./components/RosterPanel";
import Suggestions from "./components/Suggestions";
import TradeEvaluator from "./components/TradeEvaluator";
import AgentPanel from "./components/AgentPanel";

export default function App() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [team, setTeam] = useState("");
  const [error, setError] = useState("");
  // Lives here so the Suggestions panel can pre-fill the agent's question box.
  const [question, setQuestion] = useState("");

  useEffect(() => {
    api.teams()
      .then((t) => { setTeams(t); setTeam(t[0]?.name ?? ""); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">Could not load league: {error}</p>;
  if (!team) return <p>Loading league… (have you run <code>python -m app.sync</code>?)</p>;

  return (
    <main>
      <header>
        <h1>Fantasy Trade Agent</h1>
        <label>
          My team{" "}
          <select value={team} onChange={(e) => setTeam(e.target.value)}>
            {teams.map((t) => <option key={t.name}>{t.name}</option>)}
          </select>
        </label>
      </header>
      <div className="grid">
        <RosterPanel team={team} />
        <Suggestions team={team} onAsk={setQuestion} />
        <TradeEvaluator team={team} teams={teams.map((t) => t.name)} />
        <AgentPanel team={team} question={question} setQuestion={setQuestion} />
      </div>
    </main>
  );
}
