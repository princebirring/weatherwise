"""Adapter from the public API to a private Bedrock AgentCore Runtime."""

import json
import os
import re
from collections.abc import Callable, Iterator
from uuid import uuid4


class AgentCoreTeam:
    """Present an AgentCore Runtime session through the in-process team interface."""

    def __init__(self, client, runtime_arn: str, language: str, country: str = "in"):
        self.client = client
        self.runtime_arn = runtime_arn
        self.language = language
        self.country = country
        # A team is cached per website session and language by WeatherWiseApi, so this remains
        # stable for follow-up turns without exposing the browser's identifier to AgentCore.
        self.runtime_session_id = str(uuid4())
        # The conversation so far, words only. AgentCore stops an idle session's microVM after a
        # few minutes and its agent forgets; sending these lets a fresh one pick up the thread.
        # It lives only as long as this website session (24 h), like the chat itself.
        self.history: list[dict] = []

    def reply(self, message: str, on_step: Callable[[dict], None] | None = None) -> dict:
        result = None
        for event in stream_runtime(self.client, self.runtime_arn, self.runtime_session_id, {
            "type": "chat",
            "session_id": self.runtime_session_id,
            "message": message,
            "country": self.country,
            "language": self.language,
            "history": self.history[-HISTORY_TURNS:],
        }):
            if event.get("type") == "step" and on_step is not None:
                on_step({"agent": str(event.get("agent", "")), "tool": str(event.get("tool", "")),
                         "done": bool(event.get("done"))})
            elif event.get("type") == "reply":
                result = {k: v for k, v in event.items() if k != "type"}
        if not isinstance(result, dict) or not isinstance(result.get("text"), str):
            raise RuntimeError("AgentCore returned an invalid chat response")
        result["text"] = public_response_text(result["text"])
        self.history += [{"role": "user", "text": message[:MAX_TURN_CHARS]},
                         {"role": "assistant", "text": result["text"][:MAX_TURN_CHARS]}]
        return result


HISTORY_TURNS = 12      # user and assistant turns sent back (the runtime accepts up to 12)
MAX_TURN_CHARS = 4000   # per turn, the runtime's limit


def stream_runtime(client, runtime_arn: str, session_id: str, payload: dict) -> Iterator[dict]:
    """One call to the AgentCore Runtime, read as it arrives: each streamed event in turn, or the
    single JSON reply of a runtime that does not stream (an older image during a deploy)."""
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        contentType="application/json",
        accept="text/event-stream, application/json",
        payload=json.dumps(payload).encode(),
    )
    body = response["response"]
    try:
        if not response.get("contentType", "").startswith("text/event-stream"):
            raw = body.read() if hasattr(body, "read") else b"".join(body)
            yield {"type": "reply", **json.loads(raw.decode() if isinstance(raw, bytes) else raw)}
            return
        for line in body.iter_lines():
            line = line.decode() if isinstance(line, bytes) else line
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if isinstance(event, dict) and "error" in event and "type" not in event:
                    raise RuntimeError("AgentCore chat failed")  # details stay in the runtime's logs
                if isinstance(event, dict):
                    yield event
    finally:
        close = getattr(body, "close", None)
        if close is not None:
            close()


def invoke_runtime(client, runtime_arn: str, session_id: str, payload: dict):
    """One call to the AgentCore Runtime; returns its decoded JSON reply."""
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        contentType="application/json",
        payload=json.dumps(payload).encode(),
    )
    body = response["response"]
    try:
        raw = body.read() if hasattr(body, "read") else b"".join(body)
    finally:
        close = getattr(body, "close", None)
        if close is not None:
            close()
    return json.loads(raw.decode() if isinstance(raw, bytes) else raw)


def public_response_text(text: str) -> str:
    """Return only the answer when a model wraps private reasoning and response in tags."""
    response = re.search(r"<response>\s*(.*?)\s*</response>", text, flags=re.IGNORECASE | re.DOTALL)
    if response:
        return response.group(1).strip()
    return re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


class AgentCoreTeamFactory:
    """Creates a separate, private AgentCore session for each website chat session."""

    def __init__(self, client, runtime_arn: str):
        self.client = client
        self.runtime_arn = runtime_arn

    def __call__(self, _policy: dict, language: str) -> AgentCoreTeam:
        return AgentCoreTeam(self.client, self.runtime_arn, language)


def runtime_client(region: str | None = None):
    """Create a bounded client so a failed runtime cannot outlive the ALB request."""
    from boto3 import client
    from botocore.config import Config

    return client(
        "bedrock-agentcore",
        region_name=region or os.environ.get("AWS_REGION"),
        config=Config(connect_timeout=5, read_timeout=105, retries={"total_max_attempts": 1}),
    )
