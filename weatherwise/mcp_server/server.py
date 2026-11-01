"""Climate Risk MCP server (MCP Python SDK v2).

Run locally over stdio (for Claude Desktop, Kiro, or a Strands MCPClient):
    uv run python -m weatherwise.mcp_server.server
Run over streamable HTTP (for AgentCore Runtime / Gateway):
    uv run python -m weatherwise.mcp_server.server --http --port 8000
"""

import argparse

from mcp.server.mcpserver import MCPServer

from weatherwise.mcp_server.services import ClimateRiskServices

INSTRUCTIONS = """Open climate-risk tools for any location (India supported now).
- Numbers come from forecasts and history, never from the model: quote them, don't invent them.
- Official warnings (IMD and other national services) always win; rules marked "ours" are labelled.
- Always confirm a place with the person (find_place) before using it.
- In floods, never give map routes; give the shelter name, the safety line and the helpline."""

server = MCPServer("climate-risk", instructions=INSTRUCTIONS, version="0.1.0")
_services: ClimateRiskServices | None = None


def services() -> ClimateRiskServices:
    global _services
    if _services is None:
        _services = ClimateRiskServices.default()
    return _services


@server.tool()
def find_place(name: str, country_code: str = "in") -> dict:
    """Find villages or towns by name (typed or spoken). Returns candidates with district and
    state. Always read the candidates back to the person and confirm one before using it.

    Args:
        name: Place name as the person said or typed it, e.g. "Wadgaon".
        country_code: ISO country code, e.g. "in".
    """
    return services().find_place(name, country_code)


@server.tool()
def resolve_place(lat: float, lon: float) -> dict:
    """Everything derived about a point: state, district, region settings, forecast grid cell,
    elevation, terrain (plains/coast/hills), and whether a large river is nearby.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
    """
    return services().resolve_place(lat, lon)


@server.tool()
def hazard_outlook(lat: float, lon: float, place_name: str | None = None) -> dict:
    """Official warnings in force (always first), then the next days' risk at a point: the
    official heat-wave and heavy-rain rules, and our own (labelled "ours") work-heat levels
    (feels-like heat for outdoor work), excess heat, unusual rain for this place, dry spell,
    sowing and river flood, each with how many forecast runs agree; whether the flood guide
    should start (prepare or urgent); and how the forecast was corrected for this place.
    Use this before writing any warning.

    Args:
        lat: Latitude.
        lon: Longitude.
        place_name: Optional name to show, e.g. "Wadgaon, Latur".
    """
    return services().hazard_outlook(lat, lon, place_name)


@server.tool()
def official_alerts(lat: float, lon: float) -> dict:
    """Official warnings in force at a point, from IMD and the state disaster authority (via
    NDMA's SACHET), most serious first, each with its colour (red/orange/yellow/green), issuer,
    expiry and message (with translations). These always come before our own forecasts. If the
    status is "unavailable", say official warnings could not be checked: never "no warnings".

    Args:
        lat: Latitude.
        lon: Longitude.
    """
    return services().official_alerts(lat, lon)


@server.tool()
def find_shelters(lat: float, lon: float, hazard: str) -> dict:
    """Nearest verified cooling centers (heat) or shelters (flood, cyclone, other), with the
    disaster helpline. If none is near, says so and (for heat) lists nearby health facilities.
    Never returns map routes for floods.

    Args:
        lat: Latitude of the person.
        lon: Longitude of the person.
        hazard: One of "heat", "flood", "cyclone", "other".
    """
    return services().find_shelters(lat, lon, hazard)


@server.tool()
def backtest(lat: float, lon: float, first_day: str, last_day: str, place_name: str | None = None) -> dict:
    """Replay any place and dates (from 2024 on, up to 62 days): what the system would have
    sent each morning using only forecasts that existed then, what actually happened, and
    scores (hits, misses, false alarms). Before 2024: whether real conditions met our rules.

    Args:
        lat: Latitude.
        lon: Longitude.
        first_day: ISO date, e.g. "2024-07-15".
        last_day: ISO date, e.g. "2024-08-05".
        place_name: Optional label.
    """
    return services().backtest(lat, lon, first_day, last_day, place_name)


@server.tool()
def message_policy(country_code: str = "in") -> dict:
    """Helplines, message safety rules, delivery rules and safe pre-written messages for a
    country. Agents load this once and check every message they write against it.

    Args:
        country_code: ISO country code, e.g. "in".
    """
    return services().message_policy(country_code)


@server.tool()
def cap_alerts(lat: float, lon: float) -> dict:
    """Current hazard detections at a point as CAP 1.2 XML alerts (the international alert
    format used by national systems). Status is "Exercise": we are not an official service.

    Args:
        lat: Latitude.
        lon: Longitude.
    """
    return services().cap_alerts(lat, lon)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="serve streamable HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.http:
        server.run(transport="streamable-http", host=args.host, port=args.port,
                   json_response=True, stateless_http=True)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
