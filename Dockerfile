# WeatherWise API + website in one image: the JSON API (weatherwise/api), the built website,
# and the Climate Risk MCP server, which the API starts as a local process unless
# CLIMATE_RISK_MCP_URL points at a deployed one.
#
#   docker build -t weatherwise .
#   docker run -p 8080:8080 weatherwise                       # http://localhost:8080
#   docker run -p 8080:8080 -e CLIMATE_AGENT_MODEL_ID=... -e AWS_REGION=ap-south-1 weatherwise
#
# Runs as-is on App Runner, ECS/Fargate, or Lambda (add the AWS Lambda Web Adapter; see
# docs/deployment-todo.md). Not yet built on a machine with Docker: build it first.

# ---- 1. Build the website ----
FROM node:22-slim AS website
WORKDIR /website
COPY website/package.json website/package-lock.json ./
RUN npm ci
COPY website/ ./
RUN npm test && npm run build

# ---- 2. The Python app ----
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    WEATHERWISE_CACHE_DIR=/tmp/weatherwise \
    WEATHERWISE_GEODATA_DIR=/app/geodata
RUN pip install --no-cache-dir uv==0.13.6
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY weatherwise/ weatherwise/
COPY rules/ rules/
COPY data/ data/
COPY skills/ skills/
COPY evals/headline_events.toml evals/headline_events.toml
COPY --from=website /website/dist website/dist

# Ship the coastline (10 MB, Natural Earth, public domain) so no cold start downloads it.
RUN .venv/bin/python -c "from pathlib import Path; from weatherwise.places.terrain import Coastline; \
Coastline(Path('/app/geodata/ne_10m_coastline.geojson'))._load()"

RUN useradd --create-home weatherwise
USER weatherwise
EXPOSE 8080
CMD [".venv/bin/python", "-m", "weatherwise.api.server", "--host", "0.0.0.0", "--port", "8080"]
