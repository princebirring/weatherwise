"""WeatherWise API server: the JSON API, and the built website itself (website/dist).

    uv run python -m weatherwise.api.server            # http://127.0.0.1:8080
    uv run python -m weatherwise.api.server --port 9000

Settings (env):
    CLIMATE_AGENT_MODEL_ID      Bedrock model / inference profile; with AWS credentials it turns chat on.
                                Without it the site still shows places, warnings, shelters and replays.
    AWS_REGION                  Bedrock region (default us-east-2, where production runs).
    CLIMATE_RISK_MCP_URL        A deployed Climate Risk MCP server; otherwise a local one is started.
    WEATHERWISE_AGENT_RUNTIME_ARN  Optional private AgentCore Runtime ARN. When supplied,
                                website chat runs there; facts remain in this API container.
    WEATHERWISE_CACHE_DIR       Downloads and cached forecasts.
    WEATHERWISE_CACHE_BUCKET    Optional S3 bucket behind that folder, shared with the agents on
                                AgentCore and kept across deploys. The morning run (daily/) lives here too.
    WEATHERWISE_DAILY_DIR       Without the bucket: a folder from `weatherwise.daily_run --local`.
    WEATHERWISE_CHATS_PER_DAY   Daily chat cap, the AI-spend guard (default 100).
    WEATHERWISE_CHATS_PER_MINUTE  Per visitor (default 6).
    WEATHERWISE_TRUSTED_PROXY_HOPS  Our proxies in front, e.g. 1 behind the ECS load balancer.
    WEATHERWISE_BEHIND_CLOUDFRONT  1 only when CloudFront is in front: trust CloudFront-Viewer-Address.

Production runs this API on ECS Fargate behind a load balancer and AWS WAF (no CloudFront). These
limits cap chat, the only part that costs money per request.
"""

import argparse
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from weatherwise.api.backend import ROOT, AgentsOffline, BadRequest, DemoBusy, Limits, NotCovered, WeatherWiseApi

PAGE_DIR = ROOT / "website" / "dist"
LOG = logging.getLogger(__name__)


def _connect() -> tuple[WeatherWiseApi, object]:
    from weatherwise.agents.orchestrator import bedrock_model, build_team, climate_risk_client, mcp_tool_caller

    client = climate_risk_client()
    client.start()
    team_factory = None
    runtime_arn = os.environ.get("WEATHERWISE_AGENT_RUNTIME_ARN")
    if runtime_arn:
        from weatherwise.api.agentcore import AgentCoreTeamFactory, runtime_client

        team_factory = AgentCoreTeamFactory(runtime_client(), runtime_arn)
    elif os.environ.get("CLIMATE_AGENT_MODEL_ID"):
        tools, model = client.list_tools_sync(), bedrock_model()
        team_factory = lambda policy, language: build_team(model, tools, policy, language=language)  # noqa: E731
    limits = Limits(
        chats_per_day=int(os.environ.get("WEATHERWISE_CHATS_PER_DAY", Limits.chats_per_day)),
        chats_per_minute_per_visitor=int(os.environ.get("WEATHERWISE_CHATS_PER_MINUTE",
                                                        Limits.chats_per_minute_per_visitor)),
    )
    return WeatherWiseApi(mcp_tool_caller(client), team_factory, limits, daily_store=daily_store()), client


def daily_store():
    """Where the morning run's results are read from: S3 in production, a folder in development."""
    import json
    from pathlib import Path

    bucket, folder = os.environ.get("WEATHERWISE_CACHE_BUCKET"), os.environ.get("WEATHERWISE_DAILY_DIR")
    if bucket:
        import boto3

        s3 = boto3.client("s3")

        def read(name: str):
            try:
                return json.loads(s3.get_object(Bucket=bucket, Key=f"daily/{name}.json")["Body"].read())
            except s3.exceptions.NoSuchKey:
                return None
        return read
    if folder:
        def read_file(name: str):
            path = Path(folder) / f"{name}.json"
            return json.loads(path.read_text()) if path.is_file() else None
        return read_file
    return None


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
                result = await fn(request, state["backend"])
                return result if isinstance(result, Response) else JSONResponse(result)
            except Exception as e:
                body, status = error_body(e, request)
                return JSONResponse(body, status_code=status)
        return endpoint

    def run(method, *args):
        return run_in_threadpool(method, *args)

    async def chat(request: Request, b: WeatherWiseApi):
        body = await request.json()
        args = (visitor_of(request), body.get("session_id"), body.get("message"),
                body.get("language", "en"), body.get("place"))
        if "application/x-ndjson" not in request.headers.get("accept", ""):
            return await run(b.chat, *args)
        return await chat_stream(request, b, args)

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
        Route("/api/daily", handler(lambda r, b: run(b.daily))),
        Route("/api/agent-replays", handler(lambda r, b: run(b.agent_replays))),
        Route("/api/agent-replays/{replay_id}", handler(lambda r, b: run(b.agent_replay, r.path_params["replay_id"]))),
        Route("/api/chat", handler(chat), methods=["POST"]),
    ]
    if PAGE_DIR.exists():
        # Built assets have hashed names; every other path is a screen of the one-page app.
        routes.append(Mount("/assets", StaticFiles(directory=PAGE_DIR / "assets")))
        routes.append(Route("/{path:path}", _page))
    return Starlette(routes=routes, lifespan=lifespan)


def error_body(e: Exception, request: Request) -> tuple[dict, int]:
    """What the browser is told about a failure, and the status code."""
    if isinstance(e, NotCovered):  # no helpline numbers: ours belong to the countries we cover
        return {"error": "not_covered", "message": "This place is not covered yet.",
                "country_code": e.country_code, "covered_countries": e.covered_countries}, 422
    if isinstance(e, BadRequest):
        return {"error": "bad_request", "message": str(e)}, 400
    if isinstance(e, AgentsOffline):
        return {"error": "agents_offline", "message": str(e)}, 503
    if isinstance(e, DemoBusy):
        return {"error": "demo_busy", "message": str(e)}, 429
    # Keep browser errors generic. Log only the route and traceback: request bodies
    # may contain a person's message and saved location.
    LOG.error("Unhandled API error on %s", request.url.path, exc_info=e)
    return {"error": "failed", "message": "Something went wrong. "
            "For emergencies call 112. For disaster help call 1077."}, 502


async def chat_stream(request: Request, b: WeatherWiseApi, args: tuple):
    """Chat as one JSON line per event: {"type": "step", ...} while the agents work, then
    {"type": "reply", ...} or {"type": "error", ...}. A refusal (bad input, limits, agents off)
    comes before any step, so it still gets its own status code and plain JSON body."""
    loop = asyncio.get_running_loop()
    events: asyncio.Queue = asyncio.Queue()

    def on_step(step: dict) -> None:  # called from the chat's worker thread
        loop.call_soon_threadsafe(events.put_nowait, ("step", step))

    async def run_chat() -> None:
        try:
            reply = await run_in_threadpool(b.chat, *args, on_step)
            loop.call_soon_threadsafe(events.put_nowait, ("reply", reply))  # after any queued steps
        except Exception as e:  # reported to the browser below
            loop.call_soon_threadsafe(events.put_nowait, ("error", e))

    task = asyncio.create_task(run_chat())
    first = await events.get()
    if first[0] == "error":
        raise first[1]

    async def lines():
        kind, value = first
        while True:
            if kind == "error":
                body, _ = error_body(value, request)
                yield json.dumps({"type": "error", **body}) + "\n"
                break
            yield json.dumps({"type": kind, **value}) + "\n"
            if kind == "reply":
                break
            kind, value = await events.get()
        await task

    return StreamingResponse(lines(), media_type="application/x-ndjson", headers={"cache-control": "no-cache"})


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
