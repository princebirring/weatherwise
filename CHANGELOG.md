# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- "Listen" button on Today (our warning, the calm answer, official warnings) and on each
  what-to-do card: the phone reads it aloud in Marathi / Hindi / English with its own voice
  (Web Speech API; free, no AWS service). Amazon Polly was considered but has no Marathi. If the
  phone has no voice for the language, there is no button (never Marathi read by an English voice).
- Official warnings: IMD and state disaster authority alerts for the person's place, from NDMA's
  SACHET, shown first on Today in Marathi / Hindi / English (messages translated by SACHET), with
  issuer, colour and expiry. Shown even when the weather service is down; "could not check" is
  never shown as "none". An official red flood, rain or cyclone alert starts the flood guide's
  urgent mode, orange starts prepare. New MCP tool `official_alerts`; agents lead with them.
- All HTTPS calls check certificates against Mozilla's list (certifi), the same on every machine.
- Work-heat levels (ours): feels-like heat for working in the sun, "take care" (40 °C) and
  "danger" (43 °C), each with its own first advice card, in every language. Replaces the single
  humid-heat rule (`humid_heat` -> `work_heat`).
- Unusual rain (ours): rain in each place's own wettest ~2 days a year (1991-2020), so towns
  whose ~25 km forecast square never reaches IMD's national lines still get the flood guide.
- Flood guide prepare signals: heavy rain two days running at one place, and unusual rain, beside
  very heavy rain and the river. Each is named in `[flood_guide] prepare_signals`.
- Forecast correction (ours): each model's temperatures shifted by its own error at the place
  over the 30 days before each morning, capped at 3 °C; shown in `hazard_outlook` as
  `forecast_correction`.
- Switches: `[checks] enabled` lists every check; misspelt names fail at startup.
- Vijayawada 2024 flood replay.

### Changed
- "Safe to work today" replaced by "No danger found by our checks" (our checks cannot see every danger).
- Replays run the live scan's own checks (`run_checks`) and correction, so switches mean the same in both.
- The flood guide replay score (`flood_guide`, was `river_flood`) also counts flood-level rain
  as a flood: towns flood from streams and drains, not only large rivers.

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
