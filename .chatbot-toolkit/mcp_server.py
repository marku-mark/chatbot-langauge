"""Codex tools for the local chatbot graphs and offline Laravel evaluations."""

import json
import re
from pathlib import Path
from typing import Annotated, Literal

from evaluate import summarize, validate
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

ROOT = Path(__file__).resolve().parent.parent
CAPSTONE = ROOT.with_name("battlefront-capstone")
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
server = FastMCP("Battlefront chatbot toolkit")


@server.tool(annotations=READ_ONLY)
def query_chatbot_graph(
    question: Annotated[str, Field(min_length=1, max_length=300)],
    repository: Literal["chatbot-language", "capstone"] = "chatbot-language",
) -> list[dict[str, str]]:
    """Search labels and source paths in either local Graphify graph. Prefer an exact symbol or filename."""
    words = re.findall(r"\w+", question.casefold())
    if not words:
        raise ValueError("Provide a question or symbol name.")
    root = CAPSTONE if repository == "capstone" else ROOT
    graph = root / "graphify-out" / "graph.json"
    if not graph.is_file():
        raise ValueError(f"The {repository} graph is unavailable. Build its local graph before querying.")
    matches = []
    for node in json.loads(graph.read_text(encoding="utf-8"))["nodes"]:
        source = node.get("source_file")
        if not source:
            continue
        label = node["label"]
        label_matches = sum(word in label.casefold() for word in words)
        path_matches = sum(word in source.casefold() for word in words)
        score = (label.rstrip("()").casefold() == question.strip().casefold(), label_matches, path_matches)
        if any(score):
            matches.append((score, label, source, str(node.get("source_location") or "")))
    matches.sort(reverse=True)
    return [{"label": label, "source": source, "line": line} for _, label, source, line in matches[:10]]


@server.tool(annotations=READ_ONLY)
def validate_synthetic_cases(cases_json: Annotated[str, Field(max_length=100_000)]) -> dict[str, int]:
    """Validate public synthetic Laravel evaluation cases supplied as a JSON array. Use no customer data."""
    return {"valid_cases": validate(json.loads(cases_json))}


@server.tool(annotations=READ_ONLY)
def summarize_offline_evaluation(report_json: Annotated[str, Field(max_length=1_000_000)]) -> dict:
    """Summarize an offline Laravel report as counts, failed checks, and human-review status."""
    return summarize(json.loads(report_json))


@server.tool(annotations=READ_ONLY)
def capstone_improvement_workflow() -> dict[str, list[str]]:
    """Return the evaluation handoff and code entry points for improving Battlefront's multilingual chatbot."""
    return {
        "trace": [
            "Use query_chatbot_graph with repository=capstone and verify each hit in source.",
            "Start with app/Services/Chatbot/ChatbotLanguage.php for language selection.",
            "Compare app/Console/Commands/EvaluateChatbot.php and tests/Feature/ChatbotMultilingualTest.php.",
            "For gateway behavior, compare chatbot-language app/main.py and tests/test_main.py.",
        ],
        "evaluate": [
            "Create a public synthetic case for the observed behavior and an expected reply language.",
            "Keep English, Tagalog, Cebuano, and Hiligaynon distinct. Include mixed and ambiguous inputs.",
            "Run php artisan chatbot:evaluate --dataset=<local dataset> in capstone without --live.",
            "Record failed case IDs and checks. Ask a fluent speaker to review naturalness using the answer hash.",
        ],
        "boundaries": [
            "Keep Laravel authoritative for guest access, routing, catalog facts, and compatibility.",
            "Preserve deterministic private support. Use synthetic inputs and keep tokens and customer data local.",
        ],
    }


if __name__ == "__main__":
    server.run(transport="stdio")
