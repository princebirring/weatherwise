"""The Climate Risk MCP server exposes the right tools, each described for an agent."""

import asyncio

from weatherwise.mcp_server.server import server

EXPECTED = {"find_place", "resolve_place", "hazard_outlook", "official_alerts", "find_shelters", "backtest",
            "cap_alerts", "message_policy"}


def test_tools_are_registered_with_descriptions():
    tools = asyncio.run(server.list_tools())
    assert {t.name for t in tools} == EXPECTED
    for t in tools:
        assert t.description and len(t.description) > 60, t.name
        assert "properties" in t.input_schema


def test_server_instructions_carry_the_safety_rules():
    assert "never from the model" in server.instructions
    assert "Official warnings" in server.instructions
    assert "never give map routes" in server.instructions
