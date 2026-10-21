import { useEffect, useState } from "react";
import { api, Roster, TradeEvaluation } from "../api";

function toggle(list: string[], name: string) {
  return list.includes(name) ? list.filter((n) => n !== name) : [...list, name];
}

export default function TradeEvaluator({ team, teams }: { team: string; teams: string[] }) {
  const partners = teams.filter((t) => t !== team);
  const [partner, setPartner] = useState(partners[0] ?? "");
  const [mine, setMine] = useState<Roster | null>(null);
  const [theirs, setTheirs] = useState<Roster | null>(null);
  const [give, setGive] = useState<string[]>([]);
  const [get, setGet] = useState<string[]>([]);
  const [result, setResult] = useState<TradeEvaluation | null>(null);
  const [error, setError] = useState("");

  // If the user switches their own team, the partner may now be themselves.
  useEffect(() => { if (partner === team || !partner) setPartner(partners[0] ?? ""); }, [team]);
  useEffect(() => { setGive([]); setResult(null); api.roster(team).then(setMine); }, [team]);
  useEffect(() => {
    setGet([]); setResult(null);
    if (partner) api.roster(partner).then(setTheirs);
  }, [partner]);

  async function evaluate() {
    setError("");
    try { setResult(await api.evaluate(team, partner, give, get)); }
    catch (e) { setError((e as Error).message); }
  }

  const checks = (r: Roster | null, chosen: string[], set: (v: string[]) => void) =>
    r?.players.map((p) => (
      <label key={p.name} className="check">
        <input type="checkbox" checked={chosen.includes(p.name)}
               onChange={() => set(toggle(chosen, p.name))} />
        {p.position} {p.name} ({p.projected_points.toFixed(0)})
      </label>
    ));

  return (
    <section>
      <h2>Evaluate a trade</h2>
      <label>
        Trade with{" "}
        <select value={partner} onChange={(e) => setPartner(e.target.value)}>
          {partners.map((t) => <option key={t}>{t}</option>)}
        </select>
      </label>
      <div className="two-col">
        <div><h3>I give</h3>{checks(mine, give, setGive)}</div>
        <div><h3>I get</h3>{checks(theirs, get, setGet)}</div>
      </div>
      <button disabled={!give.length || !get.length} onClick={evaluate}>Evaluate</button>
      {error && <p className="error">{error}</p>}
      {result && (
        <p className={result.mutually_beneficial ? "good" : "bad"}>
          You {result.my_team.gain >= 0 ? "+" : ""}{result.my_team.gain} · Them{" "}
          {result.their_team.gain >= 0 ? "+" : ""}{result.their_team.gain} —{" "}
          {result.mutually_beneficial ? "both sides improve" : "not mutually beneficial"}
          {result.note && <span className="muted"> ({result.note})</span>}
        </p>
      )}
    </section>
  );
}
