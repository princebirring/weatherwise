# WeatherWise

[![CI](https://github.com/princebirring/weatherwise/actions/workflows/ci.yml/badge.svg)](https://github.com/princebirring/weatherwise/actions/workflows/ci.yml)
[![Licence: Apache 2.0](https://img.shields.io/badge/licence-Apache%202.0-blue.svg)](LICENSE)

Built for the AWS Builder Center hackathon *Strands SDK: Workshop to Ship* (climate resilience).
The idea, as AWS worded it:

> A heat-wave and drought early warning for smallholder farmers; a router to the nearest
> cooling center or shelter during extreme weather; a flood-risk guide that walks a household
> through how to prepare.

**Pilot:** Maharashtra, India. **Works for:** any place in India, with no per-village or per-state setup.

## The three parts
| Part | What it does |
|---|---|
| **1. Heat-wave and drought early warning** | Warns farmers days ahead: IMD heat-wave rule, humid heat, an Excess Heat Factor rule (ours, labelled), dry spells and sow-or-wait. Advice fits the crop and water source |
| **2. Cooling center / shelter router** | The nearest verified cooling center or shelter for the hazard, with the helpline. Says honestly when none is near. Never gives map routes in a flood |
| **3. Flood-risk guide** | Prepare mode, one step at a time, days ahead. Urgent mode only on an official red alert or extremely heavy rain within a day. Always "away from rivers and hill slopes" |

## How it works
```
Person (website / WhatsApp)              6 AM scheduled job (per forecast grid cell with subscribers)
          |                                              |
   Orchestrator agent  --->  Warning Agent / Flood Guide Agent    Strands Graph: risk scan -> writer
   (Strands; skills, hooks,      (specialists)                    -> final safety gate -> delivery rules
    Evaluator steering)                                                         |
          |_____________________________  MCP  _________________________________|
                                         |
                    Climate Risk MCP server (7 tools)
   find_place · resolve_place · hazard_outlook · find_shelters · backtest · cap_alerts · message_policy
                                         |
   Plain-code core (no AI): places (any point -> district, terrain, river) · risk rules · backtests
                                         |
   Open-Meteo (forecasts, river flow, history, archived forecasts, elevation) · OpenStreetMap · Natural Earth
```

**Design rules:**
- **Numbers come from data, never from the AI.** The Evaluator checks every message in code: helplines present, no "high ground" without slope safety, no map links in floods, no invented numbers.
- **Official warnings always win.** Our own rules are labelled "ours".
- **Location-agnostic.** A point goes in and everything else is derived. Work is cached per ~25 km forecast cell, so cost grows with cells, not people.
- **Only what no API can provide is written down** (`rules/`): official definitions, helplines, our safety text per language.

## Measured results (forecasts as they were issued at the time)
| Event | Result |
|---|---|
| Kolhapur flood, Jul 2024 | Flood guide started **5 days** before the river crossed its flood level; no false alarms |
| Akola heat, Apr–May 2026 | Excess Heat Factor: caught 58% of heat-wave days, 22% false alarms |
| Kharghar, Apr 16, 2023 | Real conditions met every heat rule, on a day with no official warning (conditions check only: no archived forecasts before 2024) |

Any place and dates since 2024 can be backtested the same way. Details and lessons: `docs/build-log.md`.

## Repository layout
```
weatherwise/   all code: places/, risk/, weather/, backtest/, mcp_server/, agents/, api/ (website API),
                      shelters.py, cap.py, cache.py, rules.py, runtime.py (AgentCore entry point)
rules/                global.toml · countries/in.toml · languages/{en,hi,mr}.toml
data/                 shelters_in.csv (verified shelters) · river_catchments_in.toml (pilot)
skills/               SKILL.md procedures for the agents
website/              the website: React + Vite + TypeScript (app + showcase)
evals/                scenario suite (+ headline events) and runner
tests/                unit, snapshot and live tests
scripts/              developer tools
docs/                 plan, build log, deployment-todo.md (AWS steps for DevOps)
Dockerfile            one image: website + WeatherWise API + MCP server
```

## Run it
Needs [uv](https://docs.astral.sh/uv/) (Python 3.13 is installed automatically).
```bash
uv sync
uv run pytest -m "not live"                      # offline tests
uv run pytest -m live                            # tests against the real APIs
uv run python scripts/scan_today.py              # today's outlook for the test places
uv run python scripts/scan_today.py --lat 25.59 --lon 85.14 --name Patna
uv run python scripts/backtest.py --headline     # the three headline events
uv run python -m weatherwise.mcp_server.server          # MCP server (stdio)
uv run python -m weatherwise.mcp_server.server --http   # MCP server (HTTP, port 8000)
(cd website && npm install && npm run build)             # build the website once
uv run python -m weatherwise.api.server                  # WeatherWise API + website: http://127.0.0.1:8080
```
For website development, run the API and `cd website && npm run dev` (Vite proxies `/api` to port 8080).
Website tests (every screen in English, Hindi and Marathi): `cd website && npm test`.
The site has two parts: `/` the showcase (judges, partners) and `/app` the app (farmers, households).
The agents need Claude on Amazon Bedrock:
- set `CLIMATE_AGENT_MODEL_ID` (the model or inference-profile ID from the Bedrock console) and `AWS_REGION`;
- optionally set `CLIMATE_RISK_MCP_URL` to use a deployed MCP server.

Then run `uv run python evals/run_scenarios.py`.

## Status
- **Built:** the core, the MCP server, the agents, the scheduled pipeline, backtests, tests, and the
  website (app + showcase, Marathi / Hindi / English) with its API.
- **Next:**
  - deploy to AWS and run the agents live on Bedrock: step by step in `docs/deployment-todo.md`;
  - a native speaker checks the Hindi and Marathi drafts; verified shelters.

The full plan is in `docs/planning-notes.md`.

## Contributing
Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) (including the safety
rules) and our [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems privately: see
[SECURITY.md](SECURITY.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## Licence
[Apache License 2.0](LICENSE). Data sources and their licences are listed in [NOTICE](NOTICE).

## Data and credits
- Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0), including ECMWF, GloFAS and ERA5.
- Map data © OpenStreetMap contributors (ODbL).
- Coastline from Natural Earth (public domain).

**Not an official warning service.** Always follow IMD and local authorities. Emergency 112 · Ambulance 108 · Disaster helpline 1077.
