# Fantasy Trade Agent

An AI agent that connects to an ESPN fantasy football league, analyzes every roster, and suggests trades that help both sides.

Status: Milestones 1-4 and 5a (MCP server) done. See CLAUDE.md for the plan.

## Setup
```
cp .env.example .env     # fill in your values; never commit .env
cd backend
pip install -e ".[dev]"
python -m app.sync
pytest
```

## Run the web app
```
cd backend && python -m app.sync && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev      # open http://localhost:5173
```

## MCP server
Exposes the agent's five tools to any MCP client (Claude Desktop, Claude Code, ...).
Install the extra with `pip install -e ".[mcp]"`, then add this to your client's MCP config
(adjust the paths to your machine):
```json
{
  "mcpServers": {
    "fantasy-trade-agent": {
      "command": "C:/path/to/repo/backend/.venv/Scripts/python.exe",
      "args": ["C:/path/to/repo/mcp_server/server.py"]
    }
  }
}
```
Run `python -m app.sync` first so the database has your league. The server re-reads the DB on every call.
