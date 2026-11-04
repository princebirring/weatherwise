# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

First version, built for the AWS Builder Center hackathon *Strands SDK: Workshop to Ship* and
live at https://weatherwise.online.

### Added
- **Risk checks for any place in India** (plain code, no AI): IMD heat wave; our own work-heat
  levels on feels-like heat ("take care" 40 °C, "danger" 43 °C) and Excess Heat Factor; dry spell
  and wait-before-sowing (monsoon sowing only); IMD heavy-rain categories; rain unusual for the
  place (its own wettest ~0.5% of days, never below 30 mm); river flood from GloFAS flow.
  Forecasts are corrected per model from its own errors over the previous 30 days (capped at 3 °C).
  Every check is a switch in `rules/` (`[checks] enabled`); misspelt names fail at startup.
- **Official warnings first**: IMD and state disaster authority alerts for the person's point,
  from NDMA's SACHET, shown first on Today in Marathi / Hindi / English, even when the forecast is
  down; "could not check" is never shown as "none". An official red flood, rain or cyclone alert
  starts the flood guide's urgent mode, orange starts prepare.
- **Flood guide**: prepare mode on very heavy rain, heavy rain two days running, unusual rain, a
  large river near its flood level, or an official orange alert; stays on until 7 quiet mornings.
  Urgent mode only on an official red alert or extremely heavy rain within a day.
- **Shelter router**: the nearest verified cooling center or shelter for the hazard, with the
  helpline; never a map route in a flood. The pipeline that builds the verified list from
  district disaster plans (`scripts/shelter_data.py`, `data/SHELTERS_README.md`).
- **Climate Risk MCP server** with 8 tools: `find_place`, `resolve_place`, `hazard_outlook`,
  `official_alerts`, `find_shelters`, `backtest`, `cap_alerts`, `message_policy`. Places outside
  covered countries get an honest "not covered" answer.
- **Strands agents**: Orchestrator with the Warning and Flood Guide agents as tools, skills,
  hooks (cost guard, turn clock) and the Evaluator (code safety rules + tone check, 2 rewrites,
  then the pre-written safe message).
- **The 3 AM morning run**: EventBridge Scheduler starts `weatherwise/daily_run.py`; for the 25
  places in `data/daily_watch.toml` the warning Graph runs on AgentCore Runtime and the results
  go to S3 and `/impact#live`. **AgentCore Memory** keeps what the agent told each place, so the
  next morning it writes an update, or an all-clear when the risk has eased.
- **Website** (React + Vite + TypeScript): the app (Today, danger pages, Ask, Help, flood guide)
  and the public site (how it works, impact, developers, about), every word in Marathi, Hindi and
  English. "Listen" reads warnings aloud with the phone's own voice. Ask streams the agent's steps.
- **Replays of real disasters** with forecasts as issued (`scripts/backtest.py`,
  `evals/eval_replays.py`), misses included.
- **Evals**: safety evals (`evals/eval_safety.py`), the same disasters through the real model
  (`evals/eval_agent_replays.py`: Amazon Nova Pro, 78 messages, 0 unsafe reached a household),
  and a scenario suite (`evals/run_scenarios.py`).
- **Deployment**: one CloudFormation stack (ECS Fargate behind an ALB and AWS WAF, AgentCore
  Runtime + Memory + Observability, EventBridge Scheduler, S3, Route 53 + ACM) in `us-east-2`,
  deployed by GitHub Actions through OIDC on every merge to `main`.

### Fixed
- **"Safe to work today" during a cyclone.** Replaced by "No danger found by our checks", and the
  agents can no longer tell someone they are safe (`claims_safe` rule, phrases per language).
- **A runaway agent loop.** On Nov 2, 2026 one live chat made about 1,900 model calls in 12
  minutes: the cost guard refused each tool call, but the model kept asking. Now 16 model calls
  or 12 tool requests end the loop with the pre-written safe message.
- **The tone check never saw the reply.** It ran before every tool call; it now checks the final
  reply once (10 model calls per answer became 7).
- **Made-up numbers in Marathi and Hindi** ("47 अंश", "95 प्रतिशत") are caught: unit words live in
  `rules/languages/`.
- **"Higher ground" slipped past the slope rule** (only "high ground" was matched). Found by the
  real-model replays; every delivered message is now re-checked with the current rules.
- **New places stalled on the free weather tier.** The cache is layered: the container's disk, an
  S3 bucket shared with AgentCore and kept across deploys, and a seed shipped in the image
  (`data/cache_seed/`).
- **Chat timeouts.** The turn clock stops rewrites after 45 s and the turn after 80 s.
- The `CloudFront-Viewer-Address` header is trusted only with `WEATHERWISE_BEHIND_CLOUDFRONT=1`,
  so a visitor cannot send it to dodge the per-visitor chat limit.
