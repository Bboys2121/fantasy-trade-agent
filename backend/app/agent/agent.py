"""Tool-use loop: ask Claude, run any tools it requests, send results back, repeat.

Usage (from backend/):
    python -m app.agent.agent --team "Team 1" "find me a trade for a WR"
    python -m app.agent.agent --team "Team 1"        # interactive prompt
"""
import argparse
from collections.abc import Callable
from dataclasses import dataclass, field

import anthropic

from app.agent.prompts import system_prompt
from app.agent.tools import TOOL_SCHEMAS, LeagueTools, ToolError
from app.analysis.roster_scoring import RosterPlayer
from app.config import settings

MAX_STEPS = 10  # safety cap so a confused model can't loop (and spend) forever


@dataclass
class ToolCall:
    name: str
    input: dict
    output: str
    is_error: bool = False


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)


def run_agent(question: str, my_team: str, rosters: dict[str, list[RosterPlayer]],
              client=None, on_tool_call: Callable[[ToolCall], None] | None = None) -> AgentResult:
    client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
    tools = LeagueTools(rosters)
    messages = [{"role": "user", "content": question}]
    log: list[ToolCall] = []

    for _ in range(MAX_STEPS):
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system_prompt(my_team),
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            if response.stop_reason == "max_tokens":
                text += "\n[Answer was cut off: hit the token limit.]"
            return AgentResult(text, log)

        # Keep Claude's full turn (including tool_use blocks) in the history.
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                output, is_error = tools.run(block.name, block.input), False
            except (ToolError, TypeError) as e:  # TypeError = wrong/missing arguments
                output, is_error = f"Error: {e}", True
            call = ToolCall(block.name, dict(block.input), output, is_error)
            log.append(call)
            if on_tool_call:
                on_tool_call(call)
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": output, "is_error": is_error})
        # All results for this turn go back together in ONE user message.
        messages.append({"role": "user", "content": results})

    return AgentResult("Stopped: too many tool-call steps without a final answer.", log)


def _print_call(call: ToolCall) -> None:
    preview = call.output if len(call.output) <= 200 else call.output[:200] + "..."
    print(f"  [tool] {call.name}({call.input})\n         -> {preview}")


def main() -> None:
    from app.analysis.roster_scoring import load_rosters
    from app.db.session import get_session, make_engine

    parser = argparse.ArgumentParser()
    parser.add_argument("--team", required=True, help="your fantasy team name")
    parser.add_argument("question", nargs="?", help="omit for an interactive prompt")
    args = parser.parse_args()

    if not settings.anthropic_api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY in .env first.")
    with get_session(make_engine()) as session:
        rosters = load_rosters(session)
    if args.team not in rosters:
        raise SystemExit(f"Unknown team. Choose from: {', '.join(rosters)}")

    def ask(q: str) -> None:
        result = run_agent(q, args.team, rosters, on_tool_call=_print_call)
        print(f"\n{result.answer}\n")

    if args.question:
        ask(args.question)
    else:
        while (q := input("Ask (blank to quit): ").strip()):
            ask(q)


if __name__ == "__main__":
    main()
