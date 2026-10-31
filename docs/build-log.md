# Build log

Every feature adds a dated entry: what shipped, the farmer problem it solves, the judging
criterion it serves, a metric, and what we learned (plan §14.2). The article is written from this file.

## 2026-10-29: Risk Engine, places, backtests, MCP server, agents, warning pipeline

**What shipped**
- **Risk Engine (plain code, no AI):**
  - heat wave (IMD);
  - humid heat and **Excess Heat Factor** (ours, labelled);
  - heavy rain (IMD categories);
  - dry spell and sow-or-wait;
  - river flood;
  - the flood-guide safety rule.
- **Location-agnostic places:** any coordinate → state, district, region settings, forecast grid cell, terrain (elevation + coastline) and large-river exposure. No village tables.
- **Backtest anywhere + verification:** any place and dates since 2024, using forecasts as issued by 7 models; scored as hits, misses, false alarms, POD, FAR and Brier score.
- **Climate Risk MCP server** with 6 tools:
  - `find_place`;
  - `resolve_place`;
  - `hazard_outlook`;
  - `find_shelters`;
  - `backtest`;
  - `cap_alerts` (CAP 1.2).
- **Evaluator:**
  - a code rule checker covering helplines, "high ground" without slope safety, map links in floods, made-up numbers, length, money/OTP;
  - AI tone steering;
  - the safe fallback.
- **Agents:**
  - the Orchestrator, Warning Agent and Flood Guide Agent, with 7 skills;
  - a cost-guard hook and a step-log hook.
- **Scheduled warning pipeline** as a Strands Graph: risk scan → writer (with Evaluator) → final gate → delivery rules (quiet hours, monthly cap, per-event limit) → outbox.
- **AgentCore Runtime entry point** (chat and warning modes); a 30-case scenario suite with a runner.

**Farmer problem solved:** warnings that work for any village, never invent numbers, and never tell a family to "go to high ground" or follow a map route in a flood.

**Criteria served:**
- **Technical:** pure core, interfaces, caching per grid cell, 130 offline + 6 live tests.
- **Originality:** MCP infrastructure, verification, EHF.
- **Social impact:** measured accuracy.

**Metrics (forecasts as issued):**
- **Kolhapur, Jul 2024:** flood caught **5 days** before the river crossed its flood level; POD 1.0, FAR 0.0.
- **Akola, Apr–May 2026, Excess Heat Factor:** POD 0.58, FAR 0.22.
- **Kharghar, Apr 16, 2023:** real conditions met all three heat rules, and IMD had issued no warning.
- **Latur:** the first health-facility lookup took 38 s; the next village in the same cell took 0.0 s.

**What we learned**
- **IMD's station thresholds miss on gridded forecasts.** Akola's station read 46.9°C; the grid showed ~43.6°C. A self-calibrating index (EHF) fixes much of the gap. The next step is bias-correction per cell.
- **Rivers are narrow.** Patna's own cell shows 18 m³/s; the Ganga is one cell north at 45,000 m³/s. Screen the neighbouring cells.
- **Our flood model alone must never say "move now".** It missed the 2021 Kolhapur flood, and its raw forecasts ran high a week before the 2024 one. Urgent mode needs an official alert or extremely heavy rain within a day.
- **Score flood warnings per message, not per day.** Per-day scoring made a 5-day-early warning look like 6 false alarms.
- **Free public APIs rate-limit** (Open-Meteo 429, slow Overpass). Batch requests, cache per cell, back off, use mirrors.

## 2026-10-29 (later): one package, rules not regions, MCP as the only reader

**What shipped**
- **All code in one package** (`weatherwise/`).
- **`regions/` replaced by `rules/`** (global, countries, languages) and **`data/`** (shelters, pilot river points).
  - The state level is removed.
  - The time zone is derived from the coordinates.
  - The language is the person's choice.
- **New MCP tool `message_policy`:** agents get every safety rule and safe message from the MCP server and read no files themselves. The scheduled pipeline also goes through MCP.

**Farmer problem solved:** a villager anywhere in India (e.g. Bihar) gets the same safety rules and backup messages, with no state files to forget.

**Bugs found:** in a state without its own folder, the safe fallback message used to crash, and the chat assumed Marathi. Both fixed, with tests.

**What we learned**
- **MCP is the doorway, not the knowledge.** Official rules still have to be written down once.
- **The useful question is "what can be derived?"**: time zone, language, and terrain all can.

## Oct 31: the flood guide stays on; sowing check only at monsoon sowing

**What changed**
- **The flood guide no longer switches off after one day.** Once prepare mode starts, it stays on until 7 mornings in a row show no flood signal (`stay_on_quiet_days`, ours, starting value). Urgent mode is never held over: it still needs a live red alert or extremely heavy rain.
- **Flood replays are scored per guide episode** (the guide starting is the warning; the days it stays on are preparation, not new warnings).
- **"Wait before sowing" runs only in kharif sowing time** (Jun 10 – Jul 31). After the monsoon every fortnight is dry and rabi crops are sown on stored moisture or irrigation, so "wait for rain" fired daily and was wrong.

**Measured (Kolhapur, Jul 15 – Aug 5, 2024, forecasts as issued)**
- Before: guide on Jul 21 only, off Jul 22–26 while the river rose.
- After: guide on Jul 21–27, one unbroken run through the flood on Jul 26. 1 flood caught, 0 missed, 0 false alarms, 5 days' lead.
- Heat replays unchanged (Akola Excess Heat Factor: POD 0.58, FAR 0.22).

**Honest limit:** the replay carries the guide's history day to day. The live service needs the same memory (the "active events" table in DynamoDB, plan §8.5) so the app and WhatsApp keep the guide on too; until that is deployed, a live forecast that goes quiet still turns the guide off.
