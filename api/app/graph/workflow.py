"""Bounded LangGraph orchestration with replaceable business-node handlers."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import RunState

NodeHandler = Callable[[RunState], dict[str, Any] | Awaitable[dict[str, Any]]]

NODE_NAMES = (
    "resolve_company",
    "collect",
    "extract_events",
    "compute_financials",
    "assess_outcome",
    "detect_inflections",
    "propose_hypotheses",
    "critic",
    "verify_claims",
    "match_patterns",
    "write_report",
)


async def _call(handler: NodeHandler, state: RunState) -> dict[str, Any]:
    result = handler(state)
    if inspect.isawaitable(result):
        return await result
    return result


def _status_wrapper(name: str, handler: NodeHandler) -> NodeHandler:
    async def wrapped(state: RunState) -> dict[str, Any]:
        try:
            changes = await _call(handler, state)
            statuses = dict(state.get("node_status", {}))
            statuses[name] = "done"
            return {**changes, "node_status": statuses}
        except Exception as error:  # Nodes fail clearly, rather than silently dropping data.
            statuses = dict(state.get("node_status", {}))
            statuses[name] = "failed"
            errors = [*state.get("errors", []), f"{name}: {error}"]
            return {"node_status": statuses, "errors": errors}

    return wrapped


def _after_verification(state: RunState) -> str:
    verification = state.get("verification", {})
    if verification.get("blockers") and state.get("revise_round", 0) < 2:
        return "propose_hypotheses"
    return "match_patterns"


def build_research_graph(overrides: Mapping[str, NodeHandler] | None = None):
    """Compile the full graph, allowing providers/services to replace node logic.

    The deterministic defaults make the graph testable without API keys. A real
    run injects collection, extraction, hypothesis, critic, and pattern handlers.
    """

    defaults: dict[str, NodeHandler] = {
        "resolve_company": nodes.passthrough,
        "collect": nodes.passthrough,
        "extract_events": nodes.passthrough,
        "compute_financials": nodes.compute_financials,
        "assess_outcome": nodes.assess_outcome_node,
        "detect_inflections": nodes.detect_inflections_node,
        "propose_hypotheses": nodes.passthrough,
        "critic": nodes.passthrough,
        "verify_claims": nodes.verify_claims_node,
        "match_patterns": nodes.passthrough,
        "write_report": nodes.write_report_node,
    }
    handlers = {**defaults, **(overrides or {})}
    graph = StateGraph(RunState)
    for name in NODE_NAMES:
        graph.add_node(name, _status_wrapper(name, handlers[name]))

    graph.add_edge(START, "resolve_company")
    graph.add_edge("resolve_company", "collect")
    # These nodes update different state keys and can run concurrently.
    graph.add_edge("collect", "extract_events")
    graph.add_edge("collect", "compute_financials")
    graph.add_edge(["extract_events", "compute_financials"], "assess_outcome")
    graph.add_edge("assess_outcome", "detect_inflections")
    graph.add_edge("detect_inflections", "propose_hypotheses")
    graph.add_edge("propose_hypotheses", "critic")
    graph.add_edge("critic", "verify_claims")
    graph.add_conditional_edges(
        "verify_claims",
        _after_verification,
        {"propose_hypotheses": "propose_hypotheses", "match_patterns": "match_patterns"},
    )
    graph.add_edge("match_patterns", "write_report")
    graph.add_edge("write_report", END)
    return graph.compile()
