# Fantasy Trade Agent

AI agent that reads my ESPN fantasy league, analyzes rosters, and suggests mutually beneficial trades.
Portfolio project for an AI engineering internship: the owner must be able to explain every part.

## Working rules
- One milestone at a time; stop at the end, summarize, wait.
- Briefly explain non-obvious design decisions. Simple, readable code; no needless abstractions.
- Small focused commits. Ask before adding a major dependency.
- Never print, log, hardcode, or commit `.env` secrets (ESPN cookies, API key).
- Tests use saved fixtures (`backend/tests/fixtures`), never live ESPN.

## Design
Code does the search (score rosters, find surpluses/needs, generate candidate trades).
The LLM agent does judgment (checks tools, ranks, explains both sides, drafts pitch).
`espn_client.fetch_snapshot()` returns a plain dict; `sync.load_snapshot()` loads it into SQLite.

## Commands (run from `backend/`)
- Install: `pip install -e ".[dev]"`
- Sync league: `python -m app.sync` (`--save-fixture PATH`, `--from-file PATH`)
- Trade candidates: `python -m app.analysis.trade_finder --team "Team Name"`
- Agent: `python -m app.agent.agent --team "Team Name" "find me a trade for a WR"` (needs ANTHROPIC_API_KEY)
- API: `uvicorn app.main:app --reload` (port 8000)
- Frontend (from `frontend/`): `npm install` then `npm run dev` (port 5173, proxies /api to 8000)
- MCP server: `python mcp_server/server.py` (stdio; needs `pip install -e ".[mcp]"`)
- Tests: `pytest`
