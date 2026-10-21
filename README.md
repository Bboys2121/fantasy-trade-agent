# Fantasy Trade Agent

An AI agent that connects to an ESPN fantasy football league, analyzes every roster, and suggests trades that help both sides.

Status: Milestones 1 (sync), 2 (analysis) and 3 (agent) done. See CLAUDE.md for the plan.

## Setup
```
cp .env.example .env     # fill in your values; never commit .env
cd backend
pip install -e ".[dev]"
python -m app.sync
pytest
```
