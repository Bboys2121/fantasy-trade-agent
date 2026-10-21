# Fantasy Trade Agent

An AI agent that connects to an ESPN fantasy football league, analyzes every roster, and suggests trades that help both sides.

Status: Milestones 1-4 done (sync, analysis, agent, web app). See CLAUDE.md for the plan.

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
