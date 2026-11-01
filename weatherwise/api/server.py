"""WeatherWise API server: the JSON API, and the built website itself (website/dist).

    uv run python -m weatherwise.api.server            # http://127.0.0.1:8080
    uv run python -m weatherwise.api.server --port 9000

Settings (env):
    CLIMATE_AGENT_MODEL_ID      Bedrock model / inference profile; with AWS credentials it turns chat on.
                                Without it the site still shows places, warnings, shelters and replays.
    AWS_REGION                  Bedrock region (default ap-south-1).
    CLIMATE_RISK_MCP_URL        A deployed Climate Risk MCP server; otherwise a local one is started.
    WEATHERWISE_CACHE_DIR       Downloads and cached forecasts (on Lambda: a folder under /tmp).
    WEATHERWISE_CHATS_PER_DAY   Daily chat cap, the AI-spend guard (default 100).
    WEATHERWISE_CHATS_PER_MINUTE  Per visitor (default 6).
    WEATHERWISE_TRUSTED_PROXY_HOPS  Our proxies in front, e.g. 1 behind the ECS load balancer.
    WEATHERWISE_BEHIND_CLOUDFRONT  1 only when CloudFront is in front: trust CloudFront-Viewer-Address.

The judging deployment runs this API on ECS behind a load balancer, with no CloudFront or WAF, so
these limits are the defence: they cap chat, the only part that costs money per request.
"""

import argparse
import os
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from weatherwise.api.backend import ROOT, AgentsOffline, BadRequest, DemoBusy, Limits, NotCovered, WeatherWiseApi

PAGE_DIR = ROOT / "website" / "dist"


def _connect() -> tuple[WeatherWiseApi, object]:
    from weatherwise.agents.orchestrator import bedrock_model, build_team, climate_risk_client, mcp_tool_caller

    client = climate_risk_client()
    client.start()
    team_factory = None
    if os.environ.get("CLIMATE_AGENT_MODEL_ID"):
        tools, model = client.list_tools_sync(), bedrock_model()
        team_factory = lambda policy, language: build_team(model, tools, policy, language=language)  # noqa: E731
    limits = Limits(
        chats_per_day=int(os.environ.get("WEATHERWISE_CHATS_PER_DAY", Limits.chats_per_day)),
        chats_per_minute_per_visitor=int(os.environ.get("WEATHERWISE_CHATS_PER_MINUTE",
                                                        Limits.chats_per_minute_per_visitor)),
    )
    return WeatherWiseApi(mcp_tool_caller(client), team_factory, limits), client


def visitor_of(request: Request) -> str:
    """Who is asking, for the per-visitor chat limit.

    Behind CloudFront (WEATHERWISE_BEHIND_CLOUDFRONT=1): CloudFront-Viewer-Address ("ip:port").
    Without CloudFront a browser could send that header itself, so it is ignored.
    Behind other proxies (a load balancer): WEATHERWISE_TRUSTED_PROXY_HOPS = how many
    of our own proxies append to X-Forwarded-For; the entry that many places from the right is
    the visitor. Entries further left are written by the browser and never trusted, so a visitor
    cannot dodge the limit by faking the header."""
    viewer = request.headers.get("cloudfront-viewer-address")
    if viewer and os.environ.get("WEATHERWISE_BEHIND_CLOUDFRONT") == "1":
        return viewer.rsplit(":", 1)[0]
    hops = int(os.environ.get("WEATHERWISE_TRUSTED_PROXY_HOPS", "0"))
    forwarded = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if hops and len(forwarded) >= hops:
        return forwarded[-hops]
    return request.client.host if request.client else "unknown"


def build_app(backend: WeatherWiseApi | None = None) -> Starlette:
    state: dict = {"backend": backend}

    @asynccontextmanager
    async def lifespan(app):
        client = None
        if state["backend"] is None:
            state["backend"], client = await run_in_threadpool(_connect)
        yield
        if client is not None:
            client.stop(None, None, None)

    def handler(fn):
        async def endpoint(request: Request):
            try:
                return JSONResponse(await fn(request, state["backend"]))
            except NotCovered as e:  # no helpline numbers: ours belong to the countries we cover
                return JSONResponse({"error": "not_covered", "message": "This place is not covered yet.",
                                     "country_code": e.country_code, "covered_countries": e.covered_countries},
                                    status_code=422)
            except BadRequest as e:
                return JSONResponse({"error": "bad_request", "message": str(e)}, status_code=400)
            except AgentsOffline as e:
                return JSONResponse({"error": "agents_offline", "message": str(e)}, status_code=503)
            except DemoBusy as e:
                return JSONResponse({"error": "demo_busy", "message": str(e)}, status_code=429)
            except Exception:
                return JSONResponse({"error": "failed", "message": "Something went wrong. "
                                     "For emergencies call 112. For disaster help call 1077."}, status_code=502)
        return endpoint

    def run(method, *args):
        return run_in_threadpool(method, *args)

    async def chat(request: Request, b: WeatherWiseApi):
        body = await request.json()
        return await run(b.chat, visitor_of(request), body.get("session_id"),
                         body.get("message"), body.get("language", "en"), body.get("place"))

    q = lambda r, k: r.query_params.get(k)  # noqa: E731
    routes = [
        Route("/api/status", handler(lambda r, b: run(b.status))),
        Route("/api/policy", handler(lambda r, b: run(b.policy))),
        Route("/api/places", handler(lambda r, b: run(b.find_place, q(r, "q"), q(r, "lang")))),
        Route("/api/place", handler(lambda r, b: run(b.place, q(r, "lat"), q(r, "lon")))),
        Route("/api/official", handler(lambda r, b: run(b.official, q(r, "lat"), q(r, "lon")))),
        Route("/api/shelters", handler(lambda r, b: run(b.shelters, q(r, "lat"), q(r, "lon"), q(r, "hazard")))),
        Route("/api/rules", handler(lambda r, b: run(b.rules))),
        Route("/api/replays", handler(lambda r, b: run(b.replays))),
        Route("/api/replays/{replay_id}", handler(lambda r, b: run(b.replay, r.path_params["replay_id"]))),
        Route("/api/chat", handler(chat), methods=["POST"]),
    ]
    if PAGE_DIR.exists():
        # Built assets have hashed names; every other path is a screen of the one-page app.
        routes.append(Mount("/assets", StaticFiles(directory=PAGE_DIR / "assets")))
        routes.append(Route("/{path:path}", _page))
    return Starlette(routes=routes, lifespan=lifespan)


async def _page(request: Request):
    path = request.path_params["path"]
    if path.startswith("api/"):
        return JSONResponse({"error": "not_found", "message": "Unknown API path."}, status_code=404)
    file = (PAGE_DIR / path).resolve()
    if path and file.is_file() and file.is_relative_to(PAGE_DIR.resolve()):
        return FileResponse(file)  # favicon, manifest
    return FileResponse(PAGE_DIR / "index.html", headers={"cache-control": "no-cache"})


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    # No access log: request URLs carry people's coordinates (/api/place?lat=..&lon=..).
    uvicorn.run(build_app(), host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()
