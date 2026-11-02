"""Adapter from the public API to a private Bedrock AgentCore Runtime."""

import json
import os
import re
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

    def reply(self, message: str) -> dict:
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.runtime_arn,
            runtimeSessionId=self.runtime_session_id,
            contentType="application/json",
            payload=json.dumps({
                "type": "chat",
                "session_id": self.runtime_session_id,
                "message": message,
                "country": self.country,
                "language": self.language,
            }).encode(),
        )
        body = response["response"]
        try:
            raw = body.read() if hasattr(body, "read") else b"".join(body)
        finally:
            close = getattr(body, "close", None)
            if close is not None:
                close()
        result = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        if not isinstance(result, dict) or not isinstance(result.get("text"), str):
            raise RuntimeError("AgentCore returned an invalid chat response")
        result["text"] = public_response_text(result["text"])
        return result


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
