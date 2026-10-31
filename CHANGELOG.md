# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Risk engine for any place in India: IMD heat wave, humid heat, Excess Heat Factor (ours),
  dry spell, wait-before-sowing (monsoon sowing only), heavy rain (local and upstream), river flood.
- Flood guide: prepare mode stays on until 7 quiet mornings; urgent mode only on an official red
  alert or extremely heavy rain within a day.
- Climate Risk MCP server with 7 tools: `find_place`, `resolve_place`, `hazard_outlook`,
  `find_shelters`, `backtest`, `cap_alerts`, `message_policy`. Places outside covered countries
  get an honest "not covered" answer.
- Strands agents (Orchestrator, Warning, Flood Guide) with skills, hooks and an Evaluator that
  checks every message; AgentCore Runtime entry point; 6 AM warning pipeline.
- Replays of real disasters with forecasts as issued and scores (Kolhapur 2024, Akola 2026,
  Kharghar 2023).
- WeatherWise API and website: the app for farmers and households (Start, Today, What to do,
  Safe place, Help, flood guide, Ask) and the showcase page, with a full Marathi / Hindi / English
  switch. Hindi and Marathi text are drafts awaiting a native-speaker check.
- Dockerfile and a deployment guide (`docs/deployment-todo.md`).
