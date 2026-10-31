"""Live: the scheduled pipeline and an agent tool call both go through the real MCP server."""

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fake_model import ScriptedModel
from mcp.client.stdio import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient

from weatherwise.agents.delivery import MemoryLedger, MemoryOutbox
from weatherwise.agents.orchestrator import mcp_tool_caller
from weatherwise.agents.warning_pipeline import RecipientGroupRun, WarningPipeline

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def mcp():
    client = MCPClient(lambda: stdio_client(
        StdioServerParameters(command=sys.executable, args=["-m", "weatherwise.mcp_server.server"])))
    with client:
        yield client


def test_pipeline_gets_its_facts_through_mcp(mcp):
    call = mcp_tool_caller(mcp)
    seen = []

    def outlook(lat, lon, name):
        result = call("hazard_outlook", {"lat": lat, "lon": lon, "place_name": name})
        seen.append(result)
        return result

    policy = call("message_policy", {"country_code": "in"})
    group = RecipientGroupRun("Latur", 18.40, 76.56, "en", "soybean", "well", ("farmer-1",))
    rec = WarningPipeline(outlook, ScriptedModel(["(no warning needed)"]), MemoryLedger(),
                          MemoryOutbox(), policy, with_tone_check=False).run(
        group, datetime.now(ZoneInfo("Asia/Kolkata")))
    assert seen and seen[0]["rules_version"] == policy["rules_version"]
    assert not rec.rules_version_mismatch


def test_find_place_is_cached_after_first_call(mcp):
    call = mcp_tool_caller(mcp)
    first = call("find_place", {"name": "Wadgaon"})
    second = call("find_place", {"name": "wadgaon "})
    assert first["candidates"] == second["candidates"] and first["candidates"]
