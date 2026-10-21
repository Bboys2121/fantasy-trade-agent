import { useState } from "react";
import { AgentResponse, api } from "../api";

interface Props {
  team: string;
  question: string;
  setQuestion: (q: string) => void;
}

export default function AgentPanel({ team, question, setQuestion }: Props) {
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [error, setError] = useState("");

  async function ask() {
    setLoading(true); setError(""); setResponse(null);
    try { setResponse(await api.agent(team, question)); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }

  return (
    <section className="wide">
      <h2>Ask the agent</h2>
      <textarea rows={3} value={question} placeholder='e.g. "Find me a trade for a WR"'
                onChange={(e) => setQuestion(e.target.value)} />
      <button disabled={loading || !question.trim()} onClick={ask}>
        {loading ? "Thinking…" : "Ask"}
      </button>
      {error && <p className="error">{error}</p>}
      {response && (
        <>
          <h3>Answer</h3>
          <p className="answer">{response.answer}</p>
          <h3>Agent steps ({response.tool_calls.length} tool calls)</h3>
          <ol>
            {response.tool_calls.map((c, i) => (
              <li key={i} className={c.is_error ? "bad" : ""}>
                <code>{c.name}({JSON.stringify(c.input)})</code>
                <details>
                  <summary>result</summary>
                  <pre>{c.output}</pre>
                </details>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}
