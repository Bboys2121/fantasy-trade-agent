import { useEffect, useState } from "react";
import { api, TradeCandidate } from "../api";

const POSITIONS = ["", "QB", "RB", "WR", "TE"];

export default function Suggestions({ team, onAsk }: { team: string; onAsk: (q: string) => void }) {
  const [position, setPosition] = useState("");
  const [trades, setTrades] = useState<TradeCandidate[] | null>(null);

  useEffect(() => {
    setTrades(null);
    api.trades(team, position || undefined).then((r) => setTrades(r.candidates));
  }, [team, position]);

  return (
    <section>
      <h2>Suggested trades</h2>
      <label>
        Position I want{" "}
        <select value={position} onChange={(e) => setPosition(e.target.value)}>
          {POSITIONS.map((p) => <option key={p} value={p}>{p || "Any"}</option>)}
        </select>
      </label>
      {trades === null && <p>Searching…</p>}
      {trades?.length === 0 && <p className="muted">No trades found where both teams improve.</p>}
      <ul>
        {trades?.map((t, i) => (
          <li key={i}>
            <b>{t.trade_partner}</b>: give {t.i_give.name} ({t.i_give.position}) for {t.i_get.name} (
            {t.i_get.position})
            <div className="muted">
              You +{t.my_lineup_gain} · Them +{t.their_lineup_gain}
            </div>
            <button onClick={() => onAsk(
              `Should I trade ${t.i_give.name} to ${t.trade_partner} for ${t.i_get.name}? ` +
              `Check injuries and explain why they would accept, then draft a pitch.`)}>
              Ask the agent about this
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
