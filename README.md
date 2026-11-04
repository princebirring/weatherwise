# WeatherWise

[![CI](https://github.com/princebirring/weatherwise/actions/workflows/ci.yml/badge.svg)](https://github.com/princebirring/weatherwise/actions/workflows/ci.yml)
[![Licence: Apache 2.0](https://img.shields.io/badge/licence-Apache%202.0-blue.svg)](LICENSE)
[![Live demo](https://img.shields.io/badge/live%20demo-weatherwise.online-0B5F5A.svg)](https://weatherwise.online)

**Know early. Act early.** AI weather alerts for farmers and families, built with Strands Agents on Amazon Bedrock AgentCore.

<p align="center">
  <a href="https://youtu.be/g6umKXXggMU"><img src="https://img.youtube.com/vi/g6umKXXggMU/maxresdefault.jpg" alt="Watch the 3-minute WeatherWise video on YouTube" width="760"></a>
</p>

<p align="center">
  <b><a href="https://youtu.be/g6umKXXggMU">Watch the video (2:57)</a></b> ·
  <b><a href="https://weatherwise.online">Live demo: weatherwise.online</a></b> ·
  <b><a href="https://weatherwise.online/app">Open the app</a></b> ·
  <b><a href="https://weatherwise.online/impact#live">This morning's agent run</a></b>
</p>

Built for the AWS Builder Center hackathon *Strands SDK: Workshop to Ship* (climate resilience).
The idea, as AWS worded it:

> A heat-wave and drought early warning for smallholder farmers; a router to the nearest
> cooling center or shelter during extreme weather; a flood-risk guide that walks a household
> through how to prepare.

**Works for:** any place in India, with no per-village or per-state setup. A country is one rules file (`rules/countries/in.toml`), so Africa is next.

## For judges: check it in two minutes
| What | Where |
|---|---|
| **The agent at work today** | [weatherwise.online/impact#live](https://weatherwise.online/impact#live): every morning at 3 AM IST, before people head out, EventBridge Scheduler starts [`daily_run.py`](weatherwise/daily_run.py); for 25 places across India the warning Graph runs on **AgentCore Runtime**, and the page shows every message, what the checker sent back, the model calls and the cost |
| **Memory** | **AgentCore Memory** ([`place_memory.py`](weatherwise/agents/place_memory.py)) keeps what the agent told each place, so the next morning it writes an update instead of a repeat, or an all-clear when the risk has eased (never "you are safe") |
| **Strands features** | [Graph](weatherwise/agents/warning_pipeline.py) (code risk scan → agent writers → code safety gate → delivery rules) · [MCP server](weatherwise/mcp_server/server.py) (8 tools) · [agents as tools](weatherwise/agents/orchestrator.py) · [Skills](skills/) · [hooks and Evaluator steering](weatherwise/agents/steering.py) · [evals](evals/) |
| **Proof on past disasters** | [Scorecard of every replayed event, misses included](evals/results/REPLAYS.md) (forecasts as issued then) · [the same events through the real model](evals/results/AGENT_REPLAYS.md): 78 messages from Nova Pro, 0 unsafe reached a household, $0.25 · [safety evals](evals/results/SAFETY.md) |
| **Deployment** | One CloudFormation stack ([`weatherwise-service.yaml`](infra/cloudformation/weatherwise-service.yaml)): ECS Fargate, AgentCore Runtime + Memory + Observability, EventBridge Scheduler, S3; deployed by GitHub Actions on merge |
| **Tests** | Offline tests in CI for the agents, rules, API and website (en / hi / mr) |

## The three parts
| Part | What it does |
|---|---|
| **1. Heat-wave and drought early warning** | Warns farmers days ahead: IMD heat-wave rule; our own (labelled) feels-like heat levels for work in the sun ("take care", "danger") and Excess Heat Factor; dry spells and sow-or-wait. Forecasts are corrected per place from their recent errors. Advice fits the crop and water source |
| **2. Cooling center / shelter router** | The nearest verified cooling center or shelter for the hazard, with the helpline. Says honestly when none is near. Never gives map routes in a flood |
| **3. Flood-risk guide** | Prepare mode, one step at a time, days ahead: on very heavy rain, heavy rain two days running, rain unusual for that place, a large river near its flood level, or an official orange alert. Urgent mode only on an official red alert or extremely heavy rain within a day. Always "away from rivers and hill slopes" |

## How it works
```
Person (website, Ask tab)                3 AM morning run (EventBridge Scheduler -> AgentCore Runtime)
          |                                              |
   Orchestrator agent  --->  Warning Agent / Flood Guide Agent    Strands Graph: risk scan -> writer
   (Strands; skills, hooks,      (specialists)                    -> final safety gate -> delivery rules
    Evaluator steering)                                                         |
          |_____________________________  MCP  _________________________________|
                                         |
                    Climate Risk MCP server (8 tools)
   find_place · resolve_place · hazard_outlook · official_alerts · find_shelters · backtest · cap_alerts · message_policy
                                         |
   Plain-code core (no AI): places (any point -> district, terrain, river) · risk rules · backtests
                                         |
   Open-Meteo (forecasts, river flow, history, archived forecasts, elevation) · OpenStreetMap · Natural Earth
```

**Design rules:**
- **Numbers come from data, never from the AI.** The Evaluator checks every message in code: helplines present, no "high ground" without slope safety, no map links in floods, no invented numbers, never "you are safe".
- **Official warnings always win.** Warnings from IMD and state disaster authorities (via NDMA's SACHET)
  show first on Today, in the person's language, even when our forecast is down; an official red
  flood, rain or cyclone alert starts the flood guide's urgent mode. Our own rules are labelled "ours".
- **Location-agnostic.** A point goes in and everything else is derived. Work is cached per ~25 km forecast cell, so cost grows with cells, not people.
- **Only what no API can provide is written down** (`rules/`): official definitions, helplines, our safety text per language.
- **Every check is a switch.** `[checks] enabled`, `[flood_guide] prepare_signals`, `[work_heat] levels` and
  `[forecast_correction] enabled` in `rules/global.toml` turn each piece on or off (a country can override);
  live scans and replays use the same switches, so any change can be replayed before it ships.

## Measured results
All numbers below are produced by scripts in `evals/` and can be re-run.

### Would it have warned before real disasters? (`evals/results/REPLAYS.md`)
Each event is replayed day by day with the forecasts **as they were issued at the time**.

| Event | Result |
|---|---|
| Kolhapur floods, Jul 2024 | Flood guide on **9 days** before the river crossed its flood level; no false alarms |
| Vijayawada floods, Aug 2024 | Flood guide on **2 days** before 186 mm fell. IMD's national 115.6 mm line was never forecast in the ~25 km square, so our old rules **never** started |
| Delhi heat wave, May–Jun 2024 | Warned **4 days** before the heat began; every heat-wave day caught |
| Phalodi 50 °C, May 2024 | Heat-wave warning **5 days** ahead |
| Akola heat, Apr–May 2026 | First hot spell caught on the day, not ahead; a later one 3 days ahead |
| Kharghar heatstroke, Apr 16, 2023 | Real conditions met every heat rule on a day with no official warning (no archived forecasts this early) |
| Wayanad landslides, Jul 30, 2024 | **Missed**: the forecast square showed ~53 mm; real local rain was far higher |
| Cyclone Fengal, Puducherry, Nov 30, 2024 | **Missed**: we do not model cyclones |
| Assam floods, Jul 2024 · Punjab floods, Aug 2025 | **Missed**: river floods driven by rain far upstream (Punjab's second wave was flagged 7 days ahead) |

Official warnings are shown first in the app and cover what our own checks miss. Any place and
dates since 2024 can be replayed: `uv run python scripts/backtest.py --lat .. --lon .. --from .. --to ..`.

### Does the safety check stop unsafe advice? (`evals/results/SAFETY.md`)
| What | Result |
|---|---|
| Planted mistakes caught (made-up numbers, missing helplines, "high ground" without the slope warning, map links in floods, OTP or money requests, "it is safe"), English / Marathi / Hindi | **30/30** |
| Correct drafts let through (the check does not block everything) | **15/15** |
| Unsafe drafts that reached a person through the agent loop | **0 of 6** (rewritten, or the pre-written safe message in their language) |

These use a scripted model, so they measure the code's guarantees, which hold whatever a real model writes.

### Does it hold up on the real model? (`evals/results/AGENT_REPLAYS.md`)
Seven past disasters replayed through Amazon Nova Pro on Bedrock, each morning with only the forecasts issued then.

| What | Result |
|---|---|
| Warning messages the model wrote | **78** across 7 events |
| Passed every safety rule on the first try | **65 of 78 (83%)** |
| Passed after the Evaluator sent them back | **12**; 1 never passed, so the pre-written safe message went out |
| Messages that broke a safety rule and reached a household | **0** |
| Total model cost | **$0.25** |

The most common send-back: "go to high ground" without the slope warning (10 times). That gap is why the rule lives in code.

### What our tests caught while building
- **"Safe to work today" during a cyclone.** On Oct 31 the app said this while a cyclone was in the
  news: our checks do not see what forecasters see. Official warnings now come first, and neither
  the website nor the agents ever say someone is safe.
- **A national rain line that a forecast square never reaches.** IMD's 115.6 mm "very heavy rain"
  line was never forecast for Vijayawada's square. Rain unusual *for that place* now starts the flood guide.
- **Correcting forecasts in one direction only added 9 false alarms.** The correction is now two-way.
- **Made-up numbers in Marathi and Hindi slipped through** ("47 अंश", "95 प्रतिशत"): the number check
  knew only °C, mm and %. Unit words now come from each language file.
- **The tone check never saw the reply.** It ran before every tool call (one extra model call each)
  and judged tool calls instead. It now checks the final reply once: 10 model calls per answer became 7.

### Limits
- **Warnings are not yet sent to families by text message.** Today they show in the app and on the [live run page](https://weatherwise.online/impact#live); text messages are next.
- **Misses:** very local extreme rain (Wayanad), cyclone rain and wind, and river floods driven by
  rain far upstream (Assam, Punjab). Official warnings are the safety net.
- **The "danger" heat level for work over-warns**: about 6 in 10 of its alerts in Delhi and Phalodi 2024 were false alarms.
- **Forecast squares are ~25 km**: the grid reads about 3 °C below a hot station (Akola 46.9 °C vs ~43.6 °C).
- **Terrain is coarse**: a hill village can be read as "plains" (Meppadi, Wayanad).
- **Hindi and Marathi text are drafts** until a native speaker checks them.
- **Verified shelters** cover few districts so far (district plans list them for about 4–6%).
- **Past official warnings are not archived**, so replays score only our own signals.

## Repository layout
```
weatherwise/   all code: places/, risk/, weather/, backtest/, mcp_server/, agents/, api/ (website API),
                      shelter_data/ (builds the shelter list from district disaster plans),
                      shelters.py, cap.py, cache.py, rules.py, runtime.py (AgentCore entry point)
rules/                global.toml · countries/in.toml · languages/{en,hi,mr}.toml
data/                 shelters_in.csv (verified shelters; how it is built: data/SHELTERS_README.md)
                      · shelter_sources_in.csv · review/ (drafts) · river_catchments_in.toml (pilot)
skills/               SKILL.md procedures for the agents
website/              the website: React + Vite + TypeScript (app + showcase)
evals/                safety evals, replay scorecard, scenario suite (+ events); results/ holds the reports
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
uv run python scripts/backtest.py --headline     # the website's replay events
uv run python -m evals.eval_safety               # safety evals -> evals/results/SAFETY.md
uv run python -m evals.eval_replays              # replay scorecard -> evals/results/REPLAYS.md
uv run python scripts/time_chat.py               # where one chat answer's time goes
uv run python -m weatherwise.mcp_server.server          # MCP server (stdio)
uv run python -m weatherwise.mcp_server.server --http   # MCP server (HTTP, port 8000)
(cd website && npm install && npm run build)             # build the website once
uv run python -m weatherwise.api.server                  # WeatherWise API + website: http://127.0.0.1:8080
```
For website development, run the API and `cd website && npm run dev` (Vite proxies `/api` to port 8080).
Website tests (every screen in English, Hindi and Marathi): `cd website && npm test`.
The site has two parts: `/` the showcase (judges, partners) and `/app` the app (farmers, households).
The agents need a model on Amazon Bedrock (we run Amazon Nova Pro):
- set `CLIMATE_AGENT_MODEL_ID` (e.g. `us.amazon.nova-pro-v1:0`, from the Bedrock console) and `AWS_REGION`;
- optionally set `CLIMATE_RISK_MCP_URL` to use a deployed MCP server.

Then run `uv run python evals/run_scenarios.py`.

## Status
- **Built and live** at https://weatherwise.online on AWS (ECS Fargate, deployed from `main` by GitHub Actions):
  the core, the MCP server, the agents on AgentCore Runtime with Memory and Observability, the 3 AM morning run,
  backtests, evals (scripted and real-model), and the website (app + showcase, Marathi / Hindi / English) with its API.
- **Next:**
  - warnings to families by text message;
  - Africa: a new country rules file;
  - a native speaker checks the Hindi and Marathi drafts; more verified shelters.

The full plan is in `docs/planning-notes.md`.

## Contributing
Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) (including the safety
rules) and our [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems privately: see
[SECURITY.md](SECURITY.md). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## Licence
[Apache License 2.0](LICENSE). Data sources and their licences are listed in [NOTICE](NOTICE).

## Data and credits
- Official warnings from [SACHET](https://sachet.ndma.gov.in/), National Disaster Management Authority (public domain).
- Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0), including ECMWF, GloFAS and ERA5.
- Map data © OpenStreetMap contributors (ODbL).
- Coastline from Natural Earth (public domain).

**Not an official warning service.** Always follow IMD and local authorities. Emergency 112 · Ambulance 108 · Disaster helpline 1077.
