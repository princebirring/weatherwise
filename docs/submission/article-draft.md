# WeatherWise: warning India's farmers days before heat and floods, checked against real disasters

*Built with the Strands Agents SDK on AWS for "Strands SDK: Workshop to Ship" (climate resilience).*
*Live: https://weatherwise.online · Code: https://github.com/princebirring/weatherwise (Apache-2.0)*

> DRAFT. Fill the four `[FILL]` spots once the live chat runs on Bedrock (W4 evidence).

## The problem: the people most at risk hear last

In July 2024, the river at Kolhapur crossed its danger mark on July 26. The rain that caused it
fell two days running in the Western Ghats, more than a week earlier. In April 2023, eleven or more
people died of heatstroke at an outdoor ceremony in Kharghar, on a day with no official heat-wave
warning. Warnings exist in India, but they're written for districts, in English or the state
language, for people who already know what to do with them.

A smallholder farmer needs something simpler: *will it be dangerous here, on which day, and what
can I do about it?* In their own language, on a cheap phone, days ahead.

AWS described this as three things: a heat-wave and drought early warning for smallholder
farmers, a router to the nearest cooling center or shelter, and a flood-risk guide that walks a
household through how to prepare. WeatherWise builds all three, for any place in India.

## What a person sees

Open https://weatherwise.online/app, pick a language (Marathi, Hindi or English) and a place.
**Today** gives one big answer, official warnings first (from IMD and state authorities via NDMA's
SACHET), then our own early signals for the next 7 days, labelled as ours. **What to do** shows one card at a
time, matched to the crop and water source. **Safe place** gives the nearest verified shelter, or
honestly says there isn't one and gives the helpline. In a flood, the **flood guide** walks the
household through preparing one step at a time, and switches to one short "move now" message when
officials issue a red alert. **Help** is one tap to 112 / 108 / 1077. A **Listen** button reads
everything aloud with the phone's own voice.

## How it works: AI only where it helps

The most important design decision: **numbers come from data, never from the model.**

- A **Climate Risk MCP server** (8 tools: `find_place`, `resolve_place`, `hazard_outlook`,
  `official_alerts`, `find_shelters`, `backtest`, `cap_alerts`, `message_policy`) wraps plain,
  tested code. Any point becomes a district, terrain and nearest river. Forecasts from Open-Meteo
  (ECMWF, GloFAS) are corrected per place from their own recent errors, then checked against IMD's
  official definitions and our own labelled rules. Every line lives in `rules/` and every check
  can be switched on or off.
- The **Today, Safe place and flood guide screens use no AI at all.** They're fast, cheap and checkable.
- The **Ask chat** uses a Strands agent team: an **Orchestrator** that hands off to a **Warning
  agent** (heat and drought) or a **Flood Guide agent**, each with **skills** (SKILL.md files for
  the safety procedures), **MCP tools** for every fact, a **cost-guard hook** that caps tool calls,
  and an **Evaluator** built on Strands **steering**. The Evaluator checks every draft in code
  (helplines present, no number the tools didn't return, no "go to high ground" without "away
  from hill slopes", which matters for landslides, no map links in a flood, never "you are safe")
  and sends unsafe drafts back to be rewritten. After two failed rewrites, the person gets a
  pre-written safe message in their own language. A second, AI tone check reads the final reply
  for calm, plain wording.
- A **Strands Graph** runs the 6 AM warning pipeline: risk scan → writer → final safety gate →
  delivery rules.

**On AWS:** the website and facts API run as one container on Amazon ECS (Fargate), deployed from
GitHub on every merge to `main`. The agents run on **Amazon Bedrock AgentCore Runtime** and call
**Amazon Bedrock** `[FILL: model]`. Logs and traces go to CloudWatch. The only per-request cost is
chat, which is capped in code.

## Proof: we replayed real disasters

We replayed past events day by day with the forecasts **as they were issued at the time**, so
nothing from after the day is used:

| Event | Result |
|---|---|
| Kolhapur floods, Jul 2024 | Flood guide on **9 days** before the river crossed its flood level; no false alarms |
| Vijayawada floods, Aug 2024 | On **2 days** before 186 mm fell. IMD's national "very heavy rain" line was never forecast for the city's square; rain unusual *for that place* caught it |
| Delhi heat wave, 2024 | Warned **4 days** before the heat began; every heat-wave day caught |
| Phalodi 50 °C, 2024 | Heat-wave warning **5 days** ahead |
| Wayanad landslides, 2024 · Cyclone Fengal · Assam and Punjab river floods | **Missed** (see Limits) |

And we measured the safety check by planting mistakes in drafts in all three languages:
**30/30 caught, 15/15 correct drafts let through, and no unsafe draft reached a person.**
With the real model: `[FILL: scenario pass rate]`, `[FILL: Evaluator on vs off]`.

## What our tests caught

- **"Safe to work today" during a cyclone.** On Oct 31, the app said this while a cyclone was in the
  news. Our checks can't see what forecasters see. Official warnings now come first, and the app and
  agents never tell anyone they're safe.
- **A national rain line a forecast square never reaches.** Vijayawada's square never showed IMD's
  115.6 mm, so our first version never warned. Rain unusual for that place now starts the guide.
- **Made-up numbers in Marathi and Hindi slipped through** ("47 अंश"): the checker knew only °C and mm.
- **Our tone check never saw the reply.** It ran before every tool call (an extra model call each)
  and judged the tool calls. Fixing it cut one answer from 10 model calls to 7.

## Limits, honestly

We miss very local extreme rain (Wayanad), cyclones, and river floods driven by rain far
upstream. Official warnings are the safety net there, and they're always shown first. Our "danger"
heat level for outdoor work over-warns. Forecast squares are ~25 km wide. Hindi and Marathi text
still needs a native speaker's review. Verified shelter lists exist for only a few districts.

## What's next

WhatsApp delivery for the 6 AM warnings; shelter lists from every district disaster plan;
landslide and cyclone signals; and the same design for other countries, which only needs a new
`rules/countries/` file and a language file.

`[FILL: AgentCore trace screenshot of one Marathi chat]` · `[FILL: cost per answer]`

*Not an official warning service. Always follow IMD and local authorities.*
