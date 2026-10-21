import { useEffect, useState } from "react";
import { api, Needs, Roster } from "../api";

export default function RosterPanel({ team }: { team: string }) {
  const [roster, setRoster] = useState<Roster | null>(null);
  const [needs, setNeeds] = useState<Needs | null>(null);

  useEffect(() => {
    setRoster(null);
    api.roster(team).then(setRoster);
    api.needs(team).then(setNeeds);
  }, [team]);

  return (
    <section>
      <h2>My roster</h2>
      {needs && (
        <p>
          Weakest: <b>{needs.needs_weakest_first[0]}</b> · Surplus:{" "}
          <b>{needs.surplus_positions.join(", ") || "none"}</b>
        </p>
      )}
      {roster && (
        <>
          <p className="muted">Best lineup: {roster.lineup_projected_points} projected pts</p>
          <table>
            <tbody>
              {roster.players.map((p) => (
                <tr key={p.name} className={p.starting ? "" : "bench"}>
                  <td>{p.position}</td>
                  <td>{p.name}</td>
                  <td>{p.projected_points.toFixed(1)}</td>
                  <td>{p.injury_status !== "ACTIVE" && p.injury_status !== "NORMAL" ? p.injury_status : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
