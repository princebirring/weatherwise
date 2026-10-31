# WeatherWise: Final Plan

**Hackathon:** AWS Builder Center, "Strands SDK: Workshop to Ship".
**Status:** LOCKED (Oct 27, 2026). Both teammates finished the workshop on Oct 28.

**Progress (end of Oct 29): about 55% of the build.**
- **Done:**
  - core risk rules;
  - location-agnostic places;
  - backtests + verification;
  - Climate Risk MCP server (7 tools);
  - Evaluator;
  - agents;
  - Graph warning pipeline;
  - AgentCore entry point;
  - 30/64 scenarios;
  - 137 offline + 8 live tests.

  See §8.9, `README.md` and `docs/build-log.md`.
- **Next:**
  1. Try-it page.
  2. Live Bedrock runs + scenario suite.
  3. AgentCore deploy with Prince (shared MCP server + cache, Gateway auth).
  4. Remaining 34 scenarios.
  5. WhatsApp, only if it passes the Day 4 gate.
- **Waiting on the user:** verified shelters (`data/shelters_in.csv`), Hindi/Marathi text (`rules/languages/`), CONFIRM values, source register.
- **Waiting on Prince:** Bedrock access + model ID, AWS account, Meta/WhatsApp.

---

## 1. Context
- **Goal:** win a top-3 spot (3 equal winners) AND genuinely help villagers.
- **Idea:** the hackathon's Climate resilience example, built exactly as worded (§2).
- **Pilot:** Maharashtra, India. Designed to scale to all of India.
- **Team:**
  - user (SDM): product and domain;
  - senior DevOps engineer: AWS;
  - Claude Code: writes the agent code.
- **How this plan was made:**
  - 64 village reality-test scenarios (Appendix A);
  - research on 7 real recent disasters (§12);
  - industry-standard agent design (§8.7).
- **Starting point:** the project folder is empty; everything is new code.

---

## 2. Scope
The AWS sentence, built exactly. Nothing added, nothing removed:
> "Climate resilience: a heat-wave and drought early warning for smallholder farmers; a router to the nearest cooling center or shelter during extreme weather; a flood-risk guide that walks a household through how to prepare."

| Part | What it does | Main users |
|---|---|---|
| **1. Heat-wave & drought early warning** | Warns smallholder farmers before a heat wave or drought, with what to do | Farmers |
| **2. Cooling center / shelter router** | During extreme weather, points a person to the nearest cooling center or shelter | Anyone |
| **3. Flood-risk guide** | Tells a household its flood risk and walks it through preparing | Any household |

**Decision rules**
1. If it doesn't serve one of the three parts, it doesn't go in.
2. Fix a gap only if the fix is cheap and inside the three parts. Otherwise it becomes an honest limit (§7), stated in the article.

---

## 3. Users, region and channel
1. **Region:** Maharashtra.
   - Warnings and the flood guide work statewide.
   - The shelter router has verified data in 4 pilot districts:
     - Kolhapur (river floods);
     - Raigad (cyclone, landslides, Kharghar);
     - Mumbai (city floods, humid heat);
     - Latur (drought, heat).
2. **Roles at sign-up:**
   - farmer;
   - household;
   - officer (KVK, gram panchayat, farmer group), who introduces us and forwards warnings to village groups;
   - family member (registers for a relative's village).
3. **Channel:** one WhatsApp number for all three parts (delivery rules in §5.1).
4. **Languages:**
   - chosen first at sign-up;
   - Marathi and Hindi are verified by the team;
   - other languages are labelled "machine-translated";
   - Marathi typed in English letters ("paani nahi") is understood.
5. **Location:**
   - a shared location, or a typed or spoken village name;
   - always confirmed back as "village, taluka, district: correct?";
   - "Where are you now?" updates it any time (migrant cane cutters, shepherds).
6. **Several villages:**
   - any number can register up to 5 villages (officers up to 50);
   - several family numbers can register the same village.

---

## 4. The three parts

### 4.1 Part 1: Heat-wave & drought early warning
1. **Sign-up questions:**
   - language;
   - village (confirmed);
   - crop (local names understood: harbhara, kapus, tur…);
   - water source.
2. **Lead time:**
   - heat wave: 3–7 days;
   - dry spell: 1–2 weeks;
   - drought outlook: 2–4 weeks, always labelled low-confidence.
3. **Every warning contains:**
   - what's coming, where, when, how bad, how confident we are;
   - 2–3 steps that fit the farm (crop + water source): options, not orders, aligned with IMD/KVK agromet advisories.
4. **Heat warnings also include:**
   - for people who must keep working: work 6–10 am and after 5 pm; shade every hour; water often;
   - heatstroke signs (confusion, no sweating, fainting) → cool the person, call 108;
   - elderly, pregnant women, children, chronically ill: stay indoors 12–4 pm;
   - cattle and poultry: shade and extra water.
5. **Drought warnings also include:** livestock water and fodder steps.
6. **Tone:** calm, never alarming (some districts have high farmer distress). Includes the Kisan Call Centre number for farm advice.
7. **Demo note:** there are no heat waves in November (season: Mar–Jun), so heat is shown by replaying a past heat wave. Drought is live now.

### 4.2 Part 2: Cooling center / shelter router
1. **When:**
   - any time on request (reply SHELTER);
   - automatically offered during heat waves, floods, and official alerts.
2. **Right place for the hazard:** heat → cooling center; flood, cyclone or other → shelter.
3. **What we send:**

| Situation | Reply |
|---|---|
| Heat, town or city | 3 nearest cooling centers, distance, walking directions (map link) |
| Heat, village with none nearby | "No cooling center near you" + nearest primary health center (PHC) |
| Flood | Official shelter name + "use the high road, never cross flowing water". **No map routes:** maps don't know which roads are underwater |
| Always | District disaster helpline 1077, to confirm the place is open |
| Outside pilot districts | "Call 1077" |

### 4.3 Part 3: Flood-risk guide
1. **Starts:** when the household asks (FLOOD GUIDE), or automatically when flood risk rises (§5.2, Flows 3–4).
2. **Covers:** river floods; heavy-rain, flash and city flooding.
3. **Household questions:**
   - near a river, nala, or low-lying area?
   - on or below a hill slope?
   - flooded before?
   - elderly, children, livestock, documents?
4. **Prepare mode (days ahead):**
   - one step at a time; the household replies "done" for the next;
   - it remembers where they stopped;
   - **village steps:** documents in plastic, grain up high, move cattle, charge phone, know the shelter;
   - **city steps:** move to an upper floor or terrace, avoid underpasses and open manholes, know the municipal shelter (source: NDMA urban flood guidelines).
5. **Urgent mode (hours away, or water rising):**
   - ONE short voice + text message: "Move to a safe place now, away from rivers and away from hill slopes; go to [official shelter]; call 112 / 1077."
   - Never just "go to high ground" (landslide risk).
   - No step-by-step; no map routes.
6. **Send early:**
   - while mobile networks still work;
   - tell households that government emergency phone alerts (cell broadcast) are the source during the flood itself.

### 4.4 How the parts connect
- Heat warning → "reply SHELTER" (Part 2).
- Flood warning → flood guide (Part 3) + nearest shelter (Part 2).

---

## 5. Event flows

### 5.1 Delivery rules (all warnings)
1. **Message 1 = an approved WhatsApp text template.**
   - WhatsApp lets businesses start a conversation only with pre-approved templates.
   - The template must be complete on its own (what, where, when, how bad, confidence, top 1–2 actions), because many people won't tap anything.
   - Buttons: **🔊 Listen** and **🏥 SHELTER**.
2. **Tapping 🔊 Listen** opens WhatsApp's 24-hour reply window. We then send the voice note (~40 s) and the full farm-specific steps.
3. **Footer on every message:** "Not an official warning service; follow IMD. We never ask for money or OTP."
4. **Feedback line on every warning:** "Was this useful? 1 Yes / 2 No".
5. **Recipients:**
   - everyone registered in the affected areas;
   - officers (a forward-ready copy for village groups);
   - family members registered for that village ("please call them").
6. **Timing:** normal warnings only 7 AM–8 PM IST (sent ~7–8 AM); urgent messages any time.
7. **Limits:**
   - max 4 warnings per person per month (urgent and official-alert messages exempt);
   - max 2–3 messages per event (first warning → reminder → update or cancel).
8. **How it's sent:**
   - one warning written per group (same area + crop + language + water source);
   - Evaluator check → voice note made → SQS queue sends to every member → retries on failure;
   - every send logged.

### 5.2 Flows the system starts
Thresholds below are starting values from official definitions; they are confirmed on Day 2 (§17).

**Flow 1: Heat wave (Part 1; Part 2 via SHELTER)**
1. **Trigger:** the daily 6 AM scan sees, 3–7 days ahead, either of:
   - **IMD heat-wave definition:**
     - plains: max ≥ 40°C and ≥ 4.5°C above normal, or max ≥ 45°C;
     - coast: max ≥ 37°C and ≥ 4.5°C above normal;
     - hills: max ≥ 30°C.
   - **Our humid-heat rule** (labelled as ours, not IMD's): feels-like heat in the "danger" band (≈ ≥ 41°C).
   - **Our Excess Heat Factor rule** (labelled as ours; Nairn & Fawcett 2015, used operationally by Australia's Bureau of Meteorology): the 3-day mean temperature above this place's own 95th percentile, amplified when people have not acclimatised. Added because IMD's station thresholds miss on gridded forecasts (measured: Akola Apr 2026, station 46.9°C vs grid ~43.6°C).
   - **Sent only if** at least 70% of forecast runs agree.
2. **First warning** (Day –5 to –3): the heat steps in §4.1.
3. **Reminder** (Day –1): only if still forecast.
4. **Update or cancel:** if the forecast weakens.
5. **Urgent message:** if IMD issues a red alert.
6. **SHELTER:** as in §4.2.

**Flow 2: Drought / dry spell (Part 1)**
1. **Trigger** (daily scan), either of:
   - a long dry spell forecast (≈ 10–15+ days with almost no rain) during the crop season, with low soil moisture;
   - at sowing time: dry soil + no rain in the 2-week forecast.
2. **Message:**
   - with water: protective irrigation now + mulching;
   - without water: mulching, delay sowing, or a hardier crop;
   - always: livestock water and fodder; the Kisan Call Centre number.
3. **Repeat:** a weekly update while the dry spell lasts (counts toward the cap).

**Flow 3: River flood (Part 3; Part 2)**
1. **Trigger:**
   - the river-flow forecast passes the area's flood level: the 1-in-5-year flow from the area's own river history (Kolhapur ≈ 1,300 m³/s);
   - very heavy rain in the area or at its upstream points (e.g. the Western Ghats above Kolhapur);
   - OR an official CWC/IMD flood alert.
2. **Prepare mode:** sent ~1–3 days ahead to households marked "near river / low-lying" (§4.3).
3. **Flood watch:** the daily scan switches on hourly checks for those areas.
4. **Urgent mode** (§4.3) **only** on an official red alert, or extremely heavy rain in the area or upstream within 1 day. Our river model alone only ever starts prepare mode: it is too uncertain to tell a family to move (it missed the 2021 Kolhapur flood, and its archived forecasts ran high a week before the 2024 one).
5. **End:** flood watch switches off when risk falls.

**Flow 4: Heavy rain / flash & city flooding (Part 3)**
1. **Trigger:** IMD heavy-rain categories in the forecast:
   - heavy ≥ 64.5 mm/day;
   - very heavy ≥ 115.6;
   - extremely heavy ≥ 204.5.
2. **Very heavy:** prepare-mode message to households near nalas or rivers, on or below slopes, or in cities.
3. **Extremely heavy, or an official red alert:** urgent message (slope-safe; city steps in cities).

**Flow 5: Any official alert (cyclone, cold wave, landslide, etc.) (Part 2)**
1. **Trigger:** the 30-minute check of the SACHET feed (official alerts from IMD, CWC, GSI) finds a new orange or red alert covering our users.
2. **Message:** a short summary naming the official source, + "reply SHELTER" + helpline.
3. **Rule:** we never change or soften the official meaning.

### 5.3 Flows people start
| Message | What happens |
|---|---|
| **Sign-up** | Consent first ("Can we send you warnings? Reply YES"; time saved) → language → village (confirmed) → role → farmers: crop + water source; households: near river/slope? |
| **SHELTER** | §4.2, using their saved place, a shared location, or a typed village |
| **FLOOD GUIDE** | Prepare mode (§4.3); resumes where they stopped |
| **Voice note** | Instant "ऐकत आहे… / listening…" → audio converted → Transcribe → handled like text |
| **"Where are you now?"** | Updates their location |
| **Question about a warning** | Answered from that warning's data and official sources; off-topic questions politely redirected |
| **STOP** | Stops all messages; confirms |
| **DELETE** | Deletes their profile and history; confirms |

### 5.4 Schedules and system jobs
| Job | When | What it does |
|---|---|---|
| Daily risk scan | 6:00 AM IST | Flows 1–4: new warnings, reminders, cancellations; switches flood watch on/off |
| Official alert check | Every 30 min | Flow 5; urgent messages |
| Flood watch | Hourly, only while flood risk is high | Urgent-mode trigger |
| Missed-scan alarm | If no successful daily scan in 26 h | Alerts the team |
| Clean-up | Automatic expiry rules | Voice notes deleted after a few days; Try-it sessions after 24 h |

- **If weather data is missing:**
  - never send "no risk" or cancellations;
  - keep active warnings;
  - alert the team;
  - official alerts still flow.
- **Duplicates and order:**
  - ignore repeated WhatsApp message IDs;
  - one message at a time per person;
  - rate limit per number.

---

## 6. Safety, trust, privacy and licensing

### 6.1 Message rules
1. **Official warnings always win.** We never contradict or downplay IMD. When IMD is silent but our data shows danger (e.g. coastal humid heat, Kharghar 2023), we still warn, with our confidence stated.
2. **No made-up facts.** No number is invented by AI; every number comes from data. Every action comes from an official source.
3. **Trust.** We're introduced through trusted local bodies (KVK, gram panchayat, farmer groups); our accuracy is published.

### 6.2 Privacy
1. **Consent:** opt-in only; consent time stored; a short privacy notice in Marathi/Hindi.
2. **Control:** STOP ends messages; DELETE removes all data.
3. **Protection:**
   - phone numbers encrypted (KMS);
   - data kept in India (Mumbai region);
   - secrets in Secrets Manager.
4. **Public repo:** never contains user data.
5. **Logs:** only hashed IDs. No phone numbers, names, or message text in CloudWatch.
6. **Retention and deletion** (maximum times; values marked * are confirmed on Day 2):

| Data | Where | Kept for (max) | On DELETE |
|---|---|---|---|
| Profile (encrypted number, language, villages, crop, consent time) | DynamoDB | While subscribed | Deleted at once |
| Flood-guide progress | DynamoDB | 30 days after the last step (TTL) | Deleted at once |
| Warnings-sent log (hashed ID) | DynamoDB | 90 days (TTL), for the monthly cap and accuracy stats | Deleted at once |
| Chat memory | AgentCore Memory | Shortest event expiry allowed (expected 7 days*) | Deleted for that actor at once |
| Voice notes in and out | S3 | 3 days (lifecycle rule) | Deleted at once |
| Transcribe jobs and outputs | Transcribe / S3 | Deleted right after use | n/a |
| Try-it sessions | DynamoDB | 24 h (TTL) | n/a (nothing personal) |
| Logs and traces | CloudWatch | 14 days | Contain no personal data |
| Backups | DynamoDB point-in-time recovery | 7-day window* | Deleted data ages out of backups within 7 days |
| WhatsApp copies | Meta / the user's phone | Outside our control | Stated in the privacy notice |

- **STOP** = no more messages; the profile is deleted after 30 days unless they rejoin.
- **DELETE** = everything above, immediately (backups within 7 days). The user gets a confirmation.
- Village-tester data has its own rules (§13.2).

### 6.3 Licensing and attribution
1. **Code:** Apache-2.0, with a NOTICE file. The rules require an approved OSI open-source licence; Apache-2.0 is our choice.
2. **Credits:** Open-Meteo (CC BY 4.0) in the repo, app, and article.
3. **OpenStreetMap shelter data:** ODbL (attribution + share-alike), so it lives in a separate data file under ODbL.
4. **Video:** no third-party logos or copyrighted music. The Remotion video project is kept outside the repo (Remotion isn't OSI-licensed).

### 6.4 Operational safety
1. **Kill switch per district + hazard:**
   - a flag in DynamoDB (e.g. `Kolhapur/flood = paused`), checked by the pipeline and the sender before every send;
   - one command, or a one-line console edit, flips it;
   - a global switch pauses all automatic warnings.
2. **Manual override:** the on-call person can:
   - cancel a queued warning;
   - send a correction ("Earlier message was wrong: …") to the same recipients, within 1 hour of finding an error;
   - send a hand-written message through the same rule checker.
3. **Incident owners:**
   - **content** (wrong advice, wording): the user;
   - **system** (outages, wrong recipients, cost): Prince;
   - each is the other's backup;
   - every incident gets a short note in `docs/incidents.md`.
4. **Data unavailable:** as in §5.4 (no "all clear", keep active warnings, alert the team). Users get nothing new rather than something wrong; official alerts still flow.
5. **Stale shelters:** a shelter past its re-check date (§6.5) is not named. The reply becomes "Call 1077 for the nearest open shelter" + the PHC (heat).

### 6.5 Shelter data acceptance
A shelter or cooling center enters the pack only if it has all of:

| Field | Rule |
|---|---|
| Official source | District disaster plan, municipal list, or a named official; URL or document + page |
| Coordinates | Checked on a map against the name and address |
| Hazard suitability | Marked for heat, flood, cyclone (e.g. a flood shelter must not be in a low-lying area) |
| Contact and opening status | Phone or office; "open during alerts only" noted |
| Date checked + checked by | Required |

- **Re-check:** every 30 days during the heat and monsoon seasons, 90 days otherwise; past due → treated as stale (§6.4).
- **Automated test:** CI fails if any shelter is missing a field or is past its re-check date.

---

## 7. Honest limits (stated in the article)
1. **Keypad phones:** reached through village groups and family for now; voice calls / SMS later.
2. **No network during floods:** we send early; government phone alerts cover the event itself.
3. **Tribal languages and no-network areas** (Gadchiroli, Melghat): reached through ASHA / anganwadi workers and officers.
4. **Dam-release floods:** no public data; follow district collector announcements.
5. **Nala flash floods and landslides:** not predictable by us; heavy-rain warnings and official alerts only.
6. **Fruit crops:** specific advice for the main crops only.
7. **Officers forwarding to many groups:** manual for now.
8. **Hail and cold-wave crop damage:** outside the three parts.

---

## 8. Architecture

### 8.1 How it works (plain language)
1. **Every morning** (hourly during floods, every 30 min for official alerts), plain code checks the weather and official alerts. No AI.
2. **If an area is at risk,** the AI writes one warning per group of similar people.
3. **The Evaluator** checks every message before it goes out.
4. **The warning is sent on WhatsApp** to everyone in the group (§5.1).
5. **When someone writes or speaks to us,** the Orchestrator understands it and hands it to the right specialist.

### 8.2 Agents (Strands)
| Name | Type | Job | Serves |
|---|---|---|---|
| **Orchestrator** | Agent | One door for every message: sign-up, language, village confirmation, location updates, STOP/DELETE, questions. Calls the right specialist | All |
| **Warning Agent** | Agent (worker) | Writes the warning from the risk data, farm details, and official advice: 2–3 steps, confidence, sources | Part 1 |
| **Flood Guide Agent** | Agent (worker) | Household questions; prepare mode step by step (remembers progress); urgent mode | Part 3 |
| **Evaluator** | Steering plugins (code rule checker + AI tone checker), attached to every agent that writes a message (§8.8.4) | Checks every outgoing message (§6.1, slope-safe wording, required lines, tone, length). Fail → rewrite (max 2 tries) → else a safe pre-written message | All |
| **Shelter tool** | Plain code | Picks the place type, the 3 nearest, the hazard rules, the helpline. No AI: cheaper, and it can't invent a shelter | Part 2 |

**Strands patterns**
- **Agents-as-tools:** the Orchestrator calls the specialists.
- **Graph:** the warning pipeline = Risk Engine → Warning Agent or Flood Guide Agent (Evaluator steering; rewrites on failure) → final rule gate → voice → send.
- **Why Graph, not Swarm:**
  - a swarm lets agents hand off freely and can loop and burn tokens;
  - disaster messages need a predictable, checkable path;
  - this is a "what we learned" point for the article.

**What "an agent" is:** an AI model + instructions + tools, in a loop: read → choose a tool → use it → check the result → repeat until done. Strands is AWS's open-source library that runs this loop.

### 8.3 One message, end to end
1. Sunita (Latur) sends a voice note: "खूप ऊन आहे, कुठे जाऊ?" ("It's very hot, where should I go?").
2. Transcribe turns it into text.
3. The Orchestrator understands "heat + wants a place" and loads her profile.
4. The Shelter tool returns: no cooling center within 20 km; nearest PHC 6 km; helpline 1077.
5. The Orchestrator writes a short Marathi reply with heat-safety lines.
6. The Evaluator checks: helpline? heatstroke signs? footer? calm? short? → pass.
7. The reply becomes a voice note and is sent on WhatsApp.
8. On the Try-it page, the "what the agent did" panel shows each step.

### 8.4 Non-AI components
| Component | Does | Built with |
|---|---|---|
| Risk Engine | Weather risk per area; groups people | Lambda, Open-Meteo, thresholds (§5.2) |
| Village lookup | Name → place; confirmation | Government village directory (LGD) + an open village-centre dataset; Amazon Location fallback |
| Shelter store | Pilot shelters; nearest; walking routes (heat, towns) | DynamoDB, Amazon Location |
| Official advice library | Documents agents must cite | Bedrock Knowledge Base on S3 Vectors |
| Voice in | Voice note → text | Amazon Transcribe (Marathi works in batch mode, fine for voice notes) |
| Voice out | Text → voice note | Polly (Hindi), Sarvam (Marathi) |
| Messaging | WhatsApp in/out | AWS End User Messaging Social → SNS → Lambda; SQS for sending |
| Official alerts | IMD, CWC, GSI alerts | SACHET feed (NDMA) |
| Memory | Profiles, guide progress, chat context | DynamoDB, AgentCore Memory |
| Agent hosting | Runs the agents | Bedrock AgentCore Runtime |
| Safety | PII protection | Bedrock Guardrails + Evaluator |
| Ops | Deploy, logs, traces, alarms | CDK, CloudWatch, AgentCore Observability, AWS Budgets |

### 8.5 Data, APIs and storage
**Prepared once** (the user's content → repo files → loaded by a script)
1. Villages: names from LGD + map points from an open Census-based village-centre dataset.
2. `regions/asia/india/maharashtra/`: pilot shelters, helplines, crop names, thresholds, safe fallback messages.
3. Official advice PDFs → S3 → Knowledge Base.
4. Per-area "normal" weather and usual river-flood levels: computed once from historical data → S3.

**Talking to services**
| Service | How |
|---|---|
| Open-Meteo forecast, ensemble, flood | HTTPS; many areas per call; cached in S3; retries |
| Open-Meteo Previous Runs (forecasts as issued 1–7 days earlier) | Replays only; most data from Jan 2024 |
| SACHET | RSS/CAP feed every 30 min |
| Claude on Bedrock | Through Strands; prompt caching; timeouts; retry caps |
| Transcribe, Polly, Location, Knowledge Base | AWS SDK; least-privilege permissions |
| Sarvam | HTTPS; key in Secrets Manager; falls back to the Hindi voice |
| WhatsApp | In: SNS → Lambda. Out: AWS SDK (templates + 24-h replies) |

**Where things are saved**
| Store | Contents |
|---|---|
| DynamoDB | Profiles (encrypted numbers, consent time), groups, active events, warnings sent, guide progress, shelters, villages, Try-it spend counter. Point-in-time backups on |
| S3 | Weather cache, normals, replay data, official PDFs, voice notes (auto-deleted), web page files |
| Knowledge Base (S3 Vectors) | Searchable official advice |
| AgentCore Memory | Recent conversation context |
| SQS | Outgoing message queue |
| Secrets Manager | API keys |
| CloudWatch | Logs, traces, alarms (short retention) |
| Git repo | Code, config packs, tests; never user data |

### 8.6 Engineering safeguards
1. **Try-it backend:** a Lambda Function URL with streaming, behind CloudFront + WAF. API Gateway cuts requests at 30 s, and multi-agent replies can take longer.
2. **Audio:** WhatsApp voice notes (OGG) are converted as needed for Transcribe; generated audio is converted to a WhatsApp-supported format.
3. **Failures:**
   - AI busy or throttled → safe pre-written message;
   - WhatsApp send fails → queue retries;
   - voice note not understood → "please type or try again".
4. **Tests:** CI uses saved weather snapshots (repeatable results); only replays use the live archive.
5. **Environments:**
   - dev and a frozen "judging" deployment;
   - two WhatsApp test numbers;
   - GitHub → AWS via OIDC (no stored keys).

### 8.7 Industry standards, and going beyond the workshop
| Standard | How we apply it | Criterion |
|---|---|---|
| Simplest thing that works (Anthropic, "Building effective agents") | Risk, numbers, and shelters are plain code; AI only for language and judgement | Technical |
| Known patterns | Orchestrator–workers, evaluator–optimizer, fixed Graph pipeline | Technical, Originality |
| Clear typed tools | Every tool has a schema and is tested alone | Technical |
| Guardrails + safe fallbacks | Evaluator, Bedrock Guardrails, pre-written messages | Social impact, Technical |
| Untrusted user input | Narrow tools (e.g. can only reply to the sender); prompt-injection tests | Technical |
| Evaluations | 64 scenarios + AI-judge scoring + native-speaker checks; pass rate published | Technical, Communication |
| Observability | Strands tracing → AgentCore Observability; shown in the video | Technical |
| Cost control | One warning per group, no AI on quiet days, caching; cost per farmer published | Technical, Social impact |
| Security & privacy | §6.2 | Social impact |
| Repeatable delivery | One-command CDK deploy; CI on every PR | Technical |

**Beyond the workshop (Originality):**
- Graph + agents-as-tools + evaluator loop;
- warnings sent before anyone asks;
- AgentCore Runtime, Memory, Observability;
- WhatsApp through AWS;
- Marathi voice in and out;
- official sources cited in every message;
- country packs for scale.

### 8.8 How we build it with Strands (workshop patterns → our app)
The workshop taught seven building blocks. This is how each one is used here. Learn the pattern, write our own code.

| # | Workshop block | Our use | Hard rule |
|---|---|---|---|
| 1 | Tools (`@tool`) | Shelter, village lookup, weather, profile, guide progress, advice search | Numbers and places come only from tools |
| 2 | Hooks | Cost guard, step log, sender-only | Limits live in code, not prompts |
| 3 | Skills | Heat, drought, flood-prepare, flood-urgent, shelter reply, sign-up | One skill per procedure; short system prompts |
| 4 | Steering | **The Evaluator** (rule checker + AI tone checker) | Anything that could hurt someone is checked by code |
| 5 | Session managers | Per-person chat memory; flood-guide progress | Identity comes from the WhatsApp sender, never the message text |
| 6 | Agents-as-tools | Orchestrator → Warning Agent, Flood Guide Agent | Each specialist has only the tools it needs |
| 7 | Evals | 64 scenarios as output + trajectory tests | Test the path, not just the answer |

**1. Tools**
- **The docstring is the routing logic:** a first line saying what the tool does, plus an `Args:` line per input, written for Claude.
- **Return data, not prose.** Example: `{"type": "PHC", "name": …, "km": 6, "helpline": "1077"}`. Claude writes the sentence; the tool supplies the facts.
- **Forgive input.** Village lookup accepts misspellings and English-letter Marathi, returns the closest matches, and the Orchestrator confirms back ("Wadgaon, Latur: correct?"). (Workshop lesson: `c-10002` vs `C-1001` simply failed.)
- **No tool, no capability.** The agent can only do what a tool exists for, so every user action in §5.3 has a matching tool.
- **Mock data first:** tools run on saved test data on Days 1–2, then real sources are switched in behind the same interface.

**2. Hooks** (`HookProvider`, `BeforeToolCallEvent`, `event.cancel_tool`)
1. **Cost guard:** max calls per tool per request (e.g. 3) and max loop cycles. Over the limit → cancelled with a "don't retry" message. Stops runaway Bedrock bills.
2. **Step log:** after every tool call, record the agent, tool, inputs (with personal data removed) and time. This feeds CloudWatch and the Try-it "what the agent did" panel.
3. **Sender-only:** profile, STOP and DELETE tools always act on the sender's ID from the session, whatever the model passes in. Blocks "delete user 98xxxx" prompt injection.

**3. Skills** (`AgentSkills(skills=["./skills"])`, one `SKILL.md` per folder)
- `heat-advice`, `drought-advice`, `flood-prepare-village`, `flood-prepare-city`, `flood-urgent`, `shelter-reply`, `sign-up`.
- **Skills hold the steps; packs hold the local facts.** Skills say how (e.g. "one step at a time, wait for 'done'"). Helplines, shelters and crop names stay in `regions/asia/india/maharashtra/`, so a new state needs no skill changes.
- **Progressive disclosure keeps prompts short,** which means cheaper and more accurate. Steps are sourced from the official documents (§6.1).

**4. Steering = the Evaluator** (`strands.vended_plugins.steering`)
1. **Rule checker** (`SteeringHandler`, plain code, never misses):
   - **Before tools:** no walking-route call when the hazard is flood; no send until the checks pass.
   - **On the drafted message:** required lines present (helpline, footer, heatstroke signs for heat, "away from slopes" for flood/rain); banned wording absent (only "go to high ground", any map link in a flood); every number matches the tool data; length and voice-length limits.
2. **AI tone checker** (`LLMSteeringHandler`, a second model call): calm, not alarming; options, not orders; doesn't contradict or downplay IMD; simple, natural Marathi/Hindi.
3. **On failure:** `Guide` (the agent rewrites, max 2 tries, counted by the cost-guard hook) → otherwise the safe pre-written message from the pack.
4. **Final gate:** the scheduled pipeline runs the same rule checker once more in plain code just before sending.
5. **Change from §8.2:** the Evaluator is not a separate agent. It runs as steering plugins attached to every agent that writes an outgoing message. This is the workshop's tested pattern; Strands reports steering kept 100% compliance in 600 runs vs ~82% for prompts alone.

**5. Session managers and memory**
- **Chat memory:** AgentCore Memory session manager. `actor_id` = a hashed phone number taken from the WhatsApp sender (never from the message). `session_id` = a UUID (AgentCore needs ≥ 33 characters).
- **Profile = source of truth:** language, villages, crop, water source, consent and flood-guide step are in DynamoDB, read by the profile tool. Chat memory is only for recent context.
- **Keep history short:** a sliding window of recent turns, because every saved message is re-sent to Claude on each turn (cost).
- **Scheduled warnings use no session:** each run starts fresh from the risk data.

**6. Agents-as-tools**
- **Orchestrator** tools: profile, village lookup, shelter, `warning_agent`, `flood_guide_agent`.
- **Specialist rules:**
  - each specialist is wrapped in `@tool`, and its docstring says exactly when to use it;
  - `callback_handler=None`, so only the Orchestrator replies to the user;
  - each has its own short prompt and only its own tools (the Flood Guide can't change profiles; the Warning Agent can't send);
  - each can run on a different model (§10.2).
- **Graph** (not in the workshop) runs the scheduled pipeline: Risk Engine → Warning Agent / Flood Guide Agent (with Evaluator steering) → final gate → voice → send queue.

**7. Deploy** (AgentCore Runtime)
1. **One Runtime, one entry point,** two modes chosen by the payload:
   - `{"type": "chat", …}` from the WhatsApp Lambda;
   - `{"type": "warning", "group": …}` from the scheduled Lambda.
   - Both call `invoke_agent_runtime` (boto3).
2. **Setup:** `@aws/agentcore` CLI: `create` → `add runtime` (bring your own code, Direct Code Deploy, HTTP, Bedrock) → `uv init --bare` + `uv add …` (`pyproject.toml` is required) → `deploy`.
3. **Test from the terminal:** `agentcore invoke --runtime <name> --session-id <≥33 chars> --payload '{"prompt": "…"}'`.
4. **Region:** ap-south-1 (verify, §17). Pin the CLI version in the repo, since it changed between the workshop page and the live tool.
5. **Observability:** `aws-opentelemetry-distro` sends traces automatically. Enable CloudWatch Transaction Search once per account (the workshop account wasn't allowed to).
6. **Infrastructure as code:** the CLI generates CDK. DevOps decides on Day 1 whether to keep it or fold it into our `infra/` CDK. Either way, one-command deploy.

**8. Evals** (`strands-agents-evals`)
1. **Each scenario** in Appendix A becomes a `Case`:
   - `input`: the user message, or a risk event;
   - `expected_output`: what a safe, useful reply must contain;
   - `expected_trajectory`: the tools that must be called. For example, a flood SHELTER request = village lookup → shelter, and never a route tool.
2. **`OutputEvaluator` rubric** = the §6.1 rules + the Evaluator checks. **`TrajectoryEvaluator`** = correct tools, in order.
3. **Prove the tests work:** run the same cases on a deliberately bad agent (no steering), which must score clearly lower.
4. **Plain `pytest` checks** cover anything deterministic: required lines, banned phrases, numbers match data.
5. **When they run:**
   - every PR runs a fast subset (~10 cases);
   - the full 64 + injection tests run nightly and before the feature freeze (they cost Bedrock tokens);
   - the report is saved in the repo and the pass rate is published.

### 8.9 Production architecture (decided Oct 29)
**Built and measured (Oct 29):**
- **Places:** 6 test places resolved from coordinates alone, Patna (Bihar) included. Findings:
  - rivers are narrow, so the 8 neighbouring river cells are screened;
  - "large river" = 1-in-5-year flow ≥ 1,000 m³/s; smaller rivers go through Flow 4.
- **Backtests (forecasts as issued):**
  - Kolhapur Jul 2024: flood caught 5 days before the river crossed its flood level, with no false alarms (POD 1.0, FAR 0.0).
  - Akola Apr–May 2026 (Excess Heat Factor): POD 0.58, FAR 0.22; the Apr 24 onset was seen only on the day.
  - Kharghar Apr 2023 (conditions only): every heat rule was met on Apr 16.
- **Next accuracy step:** bias-correct forecasts to each cell's own climate.
- **Code:**
  - MCP server (6 tools);
  - Evaluator rule checker + steering;
  - Orchestrator and specialists;
  - Graph pipeline with delivery rules;
  - AgentCore entry point;
  - 30-case scenario suite;
  - 130 offline + 6 live tests.

**Pitch:** anyone can build a weather chatbot. We built **open climate-risk infrastructure**: any location, any agent, forecasts scored against reality, any past day replayable. The WhatsApp/Try-it agent for Maharashtra's farmers is its **first client**. The story stays the three parts (§2); this is *how* they are delivered, never the headline.

1. **Location-agnostic: a point in, everything derived** (`places/resolve_place(lat, lon)`). No village tables, no hand-typed coordinates.
   - **Admin area:** reverse geocoding (Nominatim/OSM in dev, Amazon Location in production) → state and district → which region config applies.
   - **Grid cell:** snap to the 0.25° forecast grid, which is the cache key. ~150 villages share a cell.
   - **Terrain:** elevation (Open-Meteo elevation API) + distance to the coastline (Natural Earth) → plains/coast/hills; the cut-offs are country config.
   - **River exposure:** flood-API history at the point; a real river if its 1-in-5-year flow ≥ the country minimum. Upstream catchments (river-network data) are deferred and labelled pilot data.
   - **Village names:** two geocoders (Open-Meteo/GeoNames + Nominatim/OSM), merged, always confirmed back to the user.
2. **The unit is the grid cell, not the village.** Scale path:
   - **Stage 1 (hackathon):** scan only the cells that have subscribers, through the point API.
   - **Stage 2 (hackathon):** also scan the 8 neighbouring cells (edge hazards, warm cache for new sign-ups).
   - **Stage 3 (roadmap):** a nationwide batch job on bulk gridded data (ECMWF open data); flat cost at any user count.
3. **Climate Risk MCP server** (`climate_risk_mcp/`, MCP Python SDK v2), hosted via AgentCore Runtime/Gateway. Tools:
   - `resolve_place`;
   - `hazard_outlook`;
   - `flood_guide_status`;
   - `find_shelters`;
   - `backtest`;
   - `verification_report`;
   - `cap_alert`.

   Our Strands agents consume it through `MCPClient`, and so can any other agent (NGO, government, Claude, Kiro).
4. **Backtest anywhere:** any point, any date range from 2024 on. Day-by-day, what we would have sent, using only forecasts as issued (7-model archive) and flood levels from earlier years only. The three headline replays are just saved backtests.
5. **Verification:** every backtest is scored against what happened (reanalysis/observations):
   - hits, misses, false alarms;
   - probability of detection;
   - false-alarm ratio;
   - Brier score.

   The results are published. Live scoring keeps building through the judging period. Farmer replies ("Did it rain today?") are a later extra ground-truth source.
6. **CAP output:** every warning can also be emitted as a Common Alerting Protocol (CAP 1.2) alert, the format SACHET, NDMA and other national systems use.
7. **Interfaces for every external service** (weather, geocoder, health facilities/OSM, alerts, messaging) and a **cache interface** (files in dev; DynamoDB/S3 in production, keyed by grid cell + data version, an expiry per kind). `risk_engine/` stays pure (no I/O). Config is validated at load time.
8. **Crop water stress (FAO-56 soil water balance):** only if the user verifies the crop coefficients for 4–5 main crops by Day 3; otherwise roadmap.
9. **Part 2 stays protected:**
   - verified shelters (§6.5) + nearest health facilities from OSM when no cooling center exists;
   - district helpline;
   - no map routes in floods.

---

## 9. Interfaces

### 9.1 WhatsApp (the product)
Everything in §4–§5: sign-up, warnings, SHELTER, flood guide, voice.

### 9.2 Try-it web page (for judges and anyone)
**Purpose:** any judge, anywhere, uses the real agents in 2 minutes without WhatsApp. Our WhatsApp test number only reaches a few phones.

**Layout:** one page, mobile-first.
1. **Header:** product name + "Heat, drought & flood early warnings for Maharashtra's villages, in Marathi."
2. **Phone-style chat:**
   - the same agents as WhatsApp;
   - Marathi / Hindi / English switch;
   - text box + mic button;
   - replies with a play button for the voice note;
   - quick buttons: Sign me up, SHELTER, Flood guide, STOP.
3. **"Replay a real disaster" buttons:**
   - Kolhapur flood (Jul 2024);
   - Vidarbha heat (Apr 2026);
   - Kharghar heat (Apr 2023);
   - each shows a timeline of what the system would have sent.
4. **"What the agent did" panel:** for each reply, the agent, tools, data sources, Evaluator checks, and time taken.
5. **Results strip:** replay scores, test pass rate, cost per farmer; links to the article, repo, and video.
6. **Footer:** data credits; "Demo only: not an official warning service"; 112 / 108 / 1077.

**Rules**
1. Demo sessions never send WhatsApp messages and store nothing personal; they expire after 24 h.
2. Replays use archived data for the chosen date only.
3. **Protection:**
   - WAF rate limit per visitor;
   - a daily AI-spend cap ("demo busy, watch the video");
   - max message length.
4. Works on a cheap Android phone; loads in under 3 s on 4G.

**Built with:** React + Vite + TypeScript on S3 + CloudFront; backend as in §8.6.

**Not built:** login, officer dashboard, real sign-ups on the page.

---

## 10. Tech stack, models and cost

### 10.1 Stack
| Layer | Choice |
|---|---|
| Code | Python (Strands) for agents and engine; React + Vite + TypeScript for the Try-it page |
| Agents | Strands Agents SDK on Bedrock AgentCore (Runtime, Memory, Observability) |
| AI model | Claude on Amazon Bedrock (§10.2) |
| Advice search | Bedrock Knowledge Base on S3 Vectors (not OpenSearch Serverless: ~$170+/month even idle) |
| Data | Open-Meteo; SACHET; Amazon Location |
| Messaging | AWS End User Messaging Social (WhatsApp), SNS, SQS |
| Voice | Transcribe; Polly (Hindi); Sarvam (Marathi) |
| Compute & storage | Lambda (+ Function URL streaming), EventBridge Scheduler, DynamoDB, S3, CloudFront + WAF |
| Safety | Bedrock Guardrails + Evaluator |
| Ops | CDK, CloudWatch, AWS Budgets, GitHub Actions |
| Region | ap-south-1 (Mumbai) |

### 10.2 Models (decided)
1. Start with **Claude Opus 5.5** for all agents.
2. After the scenario tests, move the Orchestrator and Evaluator to Sonnet 5.5 or Haiku 5.5 **only where test scores hold**.
3. The team's Claude Pro plans pay for building with Claude Code; the deployed agent is billed through Bedrock.
4. **Exact Bedrock model IDs and inference profiles** are confirmed on Day 0 from the Bedrock console / `list-inference-profiles` and written into config. Never hard-coded from memory.

### 10.2a Fallbacks (each verified on Day 0–2)
| Capability | Primary | Fallback | If both fail |
|---|---|---|---|
| AI model | Claude Opus 5.5 on Bedrock | Claude Sonnet 5.5 | Safe pre-written message |
| Region | ap-south-1 (Mumbai) | Bedrock cross-region inference profile; AgentCore in the nearest supported region (stated in the privacy notice) | n/a |
| Chat memory | AgentCore Memory | Strands S3 session manager in our own bucket | Profile only (no chat context) |
| Advice search | Bedrock Knowledge Base | Curated official text inside skills | Pre-written advice from the pack |
| Voice in (Marathi) | Transcribe batch | Sarvam speech-to-text | "Please type your message" |
| Voice out | Sarvam (Marathi), Polly (Hindi) | Polly Hindi voice for both | Text only |
| Walking routes | Amazon Location | Distance + map pin link (no route) | Name + distance only |
| WhatsApp | AWS End User Messaging Social | Try-it page carries the demo | Recorded demo on a test phone |
| Weather | Open-Meteo | Cached last run | §5.4 data-missing rule |
| Official alerts | SACHET feed | On-call checks IMD/NDMA sites manually | Article states the limit |

### 10.3 Cost: hackathon month (Oct 28 – Nov 27), estimates
| Item | Estimate | Basis |
|---|---|---|
| Claude on Opus 5.5 ($4 / $20 per 1M tokens) | $150–400 | ~2,000 dev chats, ~30 test-suite runs, ~500 judge chats; low end with prompt caching |
| …if routine agents move to Sonnet 5.5 ($2 / $10) | $75–200 | Same usage |
| AgentCore Runtime + Memory | < $15 | Billed only while active |
| Lambda, DynamoDB, S3, SQS, CloudFront, WAF, EventBridge | < $15 | Mostly free tier; WAF ~$5–10 |
| CloudWatch | $5–20 | Short log retention |
| Transcribe, Polly, Location, Knowledge Base | $10–25 | Free tiers help |
| WhatsApp (AWS fee) | $10–30 | $0.005 out, $0.001 in per message |
| Sarvam | TBD | Check pricing |
| **Total** | **~$100–500** | Mostly depends on the model and caching |

- Claude prices are Anthropic list prices; confirm the Bedrock rates.
- **Paying for it:** up to $200 AWS Free Tier credits for new accounts; budget alarms at $50 / $100 / $200; prize credits if we win; the AWS Social Impact Credits application after the hackathon.
- **Cost traps avoided:** OpenSearch Serverless; NAT Gateway (keep Lambdas out of a VPC); long log retention; always-on servers; runaway agent loops (retry caps, timeouts).

### 10.4 Cost after the hackathon (10,000 farmers, rough)
- **AI:** ~1,000 groups × ≤ 4 warnings/month ≈ $40–160/month (Opus), about half on Sonnet.
- **WhatsApp:** ~40,000 warnings + replies ≈ $150–250/month.
- **≈ $0.02–0.04 (₹2–3) per farmer per month** (verify before publishing).

---

## 11. Scale
1. **Design rule:** one warning per group (area + crop + language + water source), so AI cost grows with groups, not people.
2. **Rules, not regions** (decided Oct 29). Only what no API can provide is written down, once:
   - `rules/global.toml`: our own rules;
   - `rules/countries/<iso>.toml`: official definitions and national policy (India: IMD);
   - `rules/languages/<code>.toml`: our safety text per language.
   - **No state level:** nothing varies by state. A new state needs zero files (Patna works today).
   - **Derived, not configured:** the time zone (from the coordinates); the language (the person's choice).
   - **Data, not config:** verified shelters live in a table with a district column.
   - **Only the MCP server reads these files.** Agents get them through the `message_policy` tool; the one exception is the last-resort "call 112 / 1077" line, kept in code for when the MCP server is down.
   - A country whose heat-wave definition has a different shape adds one rule function (`HEAT_WAVE_RULES`).
   - **A country file holds** (data and config only, no code changes):
   - official alert source;
   - heat and rain rules;
   - advice sources;
   - languages and voice;
   - helplines;
   - shelters;
   - channel;
   - data-protection rules.
3. **All of India:** yes. IMD, ICAR-CRIDA, NDMA, SACHET, and KVKs cover every district. Bottlenecks: shelter data and native-speaker checks.
4. **Africa:** roadmap only. Same core with new country packs; harder on languages, shelter data, and channels (SMS/USSD needed).

---

## 12. Case studies: recent disasters in Maharashtra
- Figures differ between sources, so ranges are shown.
- **Full lead-time replays** ("we'd have warned N days ahead") need forecasts-as-issued, archived mostly from Jan 2024. So:
  - **2024+ events:** full replay;
  - **2022–23 events:** shown as "the real conditions met our rules", not as lead-time claims.

| # | Event | What happened | What our app could have done | Honest limit | Replay |
|---|---|---|---|---|---|
| 1 | **Kharghar heatstroke**, Apr 16, 2023 (Raigad) | Outdoor government ceremony in noon sun and humidity: 11–14 dead, ~120–600 hospitalised. IMD had issued no heat-wave warning | Humid-heat warning to registered people and officers; heatstroke signs + 108; nearest health post | Can't change an organiser's timing | Conditions only |
| 2 | **Vidarbha heat**, May 2024 & Apr 2026 | May 2024: IMD severe heat-wave warning; Akola 45.6°C. Apr 2026: Akola 46.9°C (India's hottest); 229+ heatstroke cases statewide since Mar 1 vs ~100 in 2025 | Warnings 3–7 days ahead (work hours, water, livestock, vulnerable people); nearest PHC in villages | none | Full |
| 3 | **Drought 2026** (Marathwada worst) | 38% rain deficit in Marathwada; drought in 265 of 358 tehsils; ~45-day dry spell; ≥25% of crops damaged | Dry-spell warning ~1 week ahead (irrigation, mulching, livestock); now: sow-or-wait options | Farmers with no water have few options | Full |
| 4 | **Marathwada floods**, Sep 2025 | 128% of normal rain in bursts; ~50 to ~108 dead; 1,067+ livestock killed; ~3,960 villages affected | Prepare mode (move cattle, grain, documents, shelter); urgent mode | Sudden nala floods hard to forecast | Full |
| 5 | **Kolhapur–Sangli floods**, Jul 2024 | Jul 24: river 8 inches below the danger mark; Jul 26: crossed it; ~1.32 lakh evacuated regionally | Flood guide from Jul 24 (2+ days early); urgent mode Jul 26 | Upstream dam releases not in public data | Full |
| 6 | **Irshalwadi landslide**, Jul 19, 2023 (Raigad) | Night landslide after heavy rain: 27 dead, 57 missing | Heavy-rain warnings to hill villages: "move away from slopes; go to the official shelter" | We don't predict landslides | Conditions only |
| 7 | **2022 heat season** | 25 suspected heatstroke deaths, the most in 5 years | Heat warnings | none | Conditions only |

**Lessons that shaped the plan**
1. **Kharghar:** we warn even when IMD is silent (§6.1).
2. **Marathwada 2025:** livestock steps are in the flood guide.
3. **Irshalwadi:** never say just "go to high ground".

**Headline replay stories (decided)**
1. Kolhapur flood 2024.
2. Vidarbha heat 2026.
3. Kharghar 2023: respectful wording, no blame, focus on the missing warning.

---

## 13. Impact measurement
**Principle:** claim only what we measured.

### 13.1 Evidence, by part
| Part | Metric | How | Target |
|---|---|---|---|
| 1 | Heat-wave days warned ≥ 3 days ahead | Replay 2024–26 heat seasons; ground truth = IMD definition on recorded temperatures | Publish real number |
| 1 | False alarms | Warnings with no heat wave | Publish; keep low |
| 1 | Dry spells caught ≥ 1 week ahead | Replay 2026 dry spell and others | Publish |
| 1 | Advice traced to an official source | Automated check | 100% |
| 1–3 | Clarity in Marathi/Hindi | Team rates 30 messages 1–5 | ≥ 4/5 |
| 2 | Correct 3 nearest places | 100 test locations in pilot districts | 100% |
| 2 | Hazard rules kept | No flood routes; honest "none near you" + PHC | 100% |
| 2 | Reply time | Message in → reply out | Median < 30 s |
| 2 | Coverage | Verified places per pilot district | Publish counts |
| 3 | Early start | Kolhapur 2024 replay: guide ≥ 2 days before the danger mark? | Publish |
| 3 | Urgent mode correct | One message, < 30 s audio, slope-safe | 100% |
| 3 | Guide completion | Real testers finish prepare mode; minutes | Publish |
| All | Scenario pass rate | 64 scenarios + injection tests | Publish; 0 unsafe messages |
| All | Cost per farmer | Real AWS bill during testing | Publish |

### 13.2 Real people
1. **Who:** 5–10 village friends and relatives (with consent), on Nov 1–2.
2. **We measure:**
   - understood (can repeat the warning back);
   - would act (1–5);
   - trust (1–5);
   - voice or text preferred;
   - sign-up time.
3. **We collect:** 2–3 short quotes for the article and video (with permission).
4. **After launch:** the "Was this useful?" replies.
5. **Consent protocol:**
   1. **Script** (read in Marathi/Hindi, ~1 min):
      - who we are;
      - it's a student-style hackathon test, not a government service;
      - taking part is voluntary;
      - stop any time;
      - what we record.
   2. **Consent capture:** the tester replies "YES" on WhatsApp to a consent message (timestamped). Adults only.
   3. **Separate opt-ins** for each use: quote (name shown or anonymous), photo, voice clip. Default = anonymous; no faces without a yes.
   4. **Storage:** notes in a private team folder, never in the repo. Quotes are shown as first name + district only, with permission.
   5. **Deletion:** any tester can message "DELETE" or tell us; removed from all notes and test data within 7 days. All tester data is deleted after judging (Nov 27).

### 13.3 People potentially reached
- **Method** (shown openly, numbers verified):
  - Maharashtra farm households (Agriculture Census);
  - × share with WhatsApp in the family;
  - × realistic reach through KVKs and farmer groups.
- **Parts 2–3:** population of the pilot districts.
- **Wording:** always "potentially reached", never "lives saved".

### 13.4 Headline lines for the article (filled with real numbers)
- "In replays of real 2024–26 heat waves, we warned on X of Y heat-wave days at least 3 days ahead (Z% false alarms)."
- "In the July 2024 Kolhapur flood, the guide would have started N days before the river crossed the danger mark."
- "0 unsafe messages in N tests; 100% of advice traced to official sources."
- "N villagers tested it: X% understood it, Y% said they would act."
- "About ₹2–3 per farmer per month."

---

## 14. Hackathon requirements

### 14.1 Rules that affect us
1. **Workshop first:**
   - both teammates complete "Building AI Agents with Strands SDK: From Simple Loops to Multi-Agent Swarms" inside the window, before building (Rules tab: "complete the Strands Agents SDK workshop and then build and ship a working AI agent on AWS"; failing it is pass/fail disqualification);
   - URL: catalog.us-east-1.prod.workshops.aws/workshops/083b80d7-5a90-402b-9bb4-19fb53092808;
   - start no earlier than Oct 28, 12:30 PM IST (12:00 AM PDT);
   - screenshot the completion;
   - learn its patterns, don't copy its code;
   - never deploy our app in its temporary sandbox;
   - paste its module list into the article notes afterwards.
2. **Original agent:** built with Strands, running on AWS (Rules tab: "a working AI agent on AWS"), not previously published.
3. **Deadline:** Nov 4, 11:59 PM PT = **Nov 5, 1:29 PM IST**. We submit by Nov 4, ~6 PM IST.
4. **Eligibility:** finalists are checked against LinkedIn and other public profiles, so country and employment must be accurate.
5. **Licence:** the repo must be public under an approved OSI licence (we use Apache-2.0).

### 14.2 Deliverables
| # | Required (pass/fail) | Our version |
|---|---|---|
| 1 | Workshop completed by both | Screenshots |
| 2 | Working Strands agent on AWS | §8 |
| 3 | Builder Center article | Drafted from `docs/build-log.md` with the `technical-article-writer` skill; headings mirror the judging criteria and the Social Impact form |
| 4 | Public repo, OSI license | Apache-2.0; README with architecture diagram, one-command deploy, cost per farmer |
| 5 | Public video < 3 min (YouTube/Vimeo) | Real screen recordings + Remotion scenes; our own voices (a Marathi line) |

**Extras that win:** the live Try-it link; published test pass rate; the 3 replay stories.

**Build log rule:** every feature PR adds a dated entry to `docs/build-log.md`:
- what shipped;
- the farmer problem it solves;
- the judging criterion it serves;
- a metric or screenshot;
- what we learned.

Enforced by a PR template + CI check.

### 14.3 Submission control sheet
Kept at the top of `docs/submission.md`. **Submission owner: the user**; backup: Prince.

| Item | URL / proof | Owner | Ready by (IST) | ✓ |
|---|---|---|---|---|
| Workshop proof: user | Screenshots (Module 5 invoke + Wrap-Up) | User | Oct 28 | |
| Workshop proof: Prince | Screenshots | Prince | Oct 28 | |
| Builder Center article (published, public) | | User | Nov 4, 12 PM | |
| Public repo (OSI licence, README, no secrets or user data) | | Prince | Nov 4, 12 PM | |
| Demo video < 3 min (public on YouTube) | | User | Nov 4, 2 PM | |
| Try-it demo (live, judging deployment frozen) | | Prince | Nov 3, 6 PM | |
| Submission form filled; all links opened in a private window | | User | **Nov 4, 6 PM** | |

**Final checklist (Nov 4):**
1. Every link opens logged out.
2. The video is public, not unlisted.
3. The repo is public with a LICENSE.
4. A secrets scan is clean.
5. The article links the repo, video and demo.
6. The Try-it page works on a phone.
7. Spend caps are on.

---

## 15. Execution

### 15.1 Tools
- Official `strands-agents-mcp-server`, which gives Claude Code live Strands docs.
- Packages: `strands-agents`, `strands-agents-tools`, `bedrock-agentcore`, `aws-opentelemetry-distro` (traces to CloudWatch), `strands-agents-evals`.
- Deploy CLI: `@aws/agentcore` (npm; `create` → `add` → `deploy` → `invoke`; builds from `pyproject.toml` via `uv`). The old `bedrock-agentcore-starter-toolkit` CLI is replaced: don't use it.
- AgentCore session IDs must be ≥ 33 characters: use a UUID or a padded hash of the phone number, never the raw number.
- Reference: `aws-samples/sample-strands-agent-with-agentcore` (review before use).

### 15.2 Before Day 1 (Oct 27): admin only, no project code
| # | Task | Owner |
|---|---|---|
| 1 | Join the hackathon; profiles show the correct country | Both |
| 2 | Team AWS account; budget alarms $50 / $100 / $200 | DevOps |
| 3 | Bedrock: request Claude access (Mumbai or cross-region); check and raise tokens-per-minute limits | DevOps |
| 4 | Meta Business account + two WhatsApp test numbers via AWS End User Messaging Social; start display-name and business verification | DevOps |
| 5 | Draft message templates (Marathi, Hindi, English): warning, reminder, update/cancel, urgent, official-alert summary, consent; submit for approval | User drafts, DevOps submits |
| 6 | Choose the product name | User |
| 7 | Email Open-Meteo to confirm non-commercial use | User |
| 8 | Sarvam account; check terms and pricing | User |
| 9 | Line up 5–10 village testers for Nov 1–2 | User |

### 15.3 User's content checklist (Days 1–3)
1. Shelters and cooling centers for the 4 pilot districts, each passing the §6.5 acceptance fields.
2. Helplines (1077 per district, 108, 112, Kisan Call Centre).
3. Official advice PDFs (IMD/KVK advisories, ICAR-CRIDA plans, NDMA heat and flood guidance, Maharashtra heat action plan).
4. Local crop names.
5. Flood prep steps (village + city) from NDMA.
6. Safe pre-written fallback messages in Marathi and Hindi.
7. Confirm all thresholds in §5.2 against official definitions.

### 15.4 8-day plan (IST)
| Day | User | DevOps | Claude Code |
|---|---|---|---|
| **D1, Oct 28** | **Workshop first** (from 12:30 PM). Content items 1–3 | **Workshop first.** CDK skeleton; hello Strands agent on AgentCore | After the workshop: repo (Apache-2.0, NOTICE, CI, PR template, build log); Strands MCP server; scaffold |
| **D2, Oct 29** | Content items 4–7; start the source register (§17) | DynamoDB (+ backups, TTLs), S3 lifecycle, SQS, the 3 schedules, missed-scan alarm, kill-switch flags; WhatsApp → SNS → Lambda echo | Risk Engine + tools (weather, village lookup, shelter, profile) with unit tests |
| **D3, Oct 30** | Finish pilot shelter data; review first Marathi messages and skill steps | Knowledge Base (S3 Vectors) + official PDFs; Guardrails | Orchestrator, Warning Agent, hooks, skills, Evaluator steering; first WhatsApp text in → reply |
| **D4, Oct 31** | Review flood-guide wording (village, city, slope-safe) | Transcribe/Polly/Sarvam; Secrets Manager; KMS | Flood Guide Agent; Graph pipeline; Flows 1–5; voice in/out |
| **D5, Nov 1** | **Village test session 1** | Try-it hosting (S3, CloudFront, WAF, Function URL, spend cap) | Try-it page; scenario runner + 64 scenarios + injection tests in CI |
| **D6, Nov 2** | **Village test session 2**; quotes; rate 30 messages | Load test (20 parallel chats); alarms; daily health check | Replays + 2024–26 heat score; fixes; model-tier test; cost per farmer |
| **D7, Nov 3** | **Feature freeze 12 PM.** Article draft | Frozen judging deployment | Bug fixes only; README + diagram; video scenes + recordings |
| **D8, Nov 4** | Publish article; final video; YouTube (public) | Final health check; repo public | Submission checklist |
| **Submit** | **By Nov 4, ~6 PM IST** | | |

### 15.5 Must ship vs cut list
**Scope rule:** this is a production-grade plan in an 8-day window. The demo proof comes first; production integrations get cut before it.

**Must ship (never cut)**
0. **Climate Risk MCP server** with location-agnostic `resolve_place`, backtest anywhere, verification report (§8.9).
1. **Try-it page:** all three parts end to end (Marathi/Hindi/English text), deployed on AWS. This is the non-negotiable proof.
2. **The 3 headline replays** (Kolhapur 2024, Vidarbha 2026, Kharghar 2023).
3. **Evaluator safety evidence:** steering rules + the scenario suite in CI + published pass rate + the bad-agent baseline.
4. **The scheduled warning pipeline** (Graph) running on replay data.
5. **Submission:** workshop proof; article, repo, and video submitted (§14.3).

**Build order (from Oct 29):** places + cache → MCP tools (risk, flood guide, shelters, CAP) → backtest + verification → heat replays → Strands agents (Orchestrator, Warning, Flood Guide, Evaluator steering) via MCPClient → Graph pipeline → 64-scenario evals → Try-it page → AgentCore deploy.

**Cut in this order if behind** (production integrations go first)
1. Sarvam Marathi voice → Marathi text + Hindi voice.
2. Live SACHET feed → official alerts shown in replays only.
3. Knowledge Base → curated official text in skills (§10.2a).
4. Voice in (Transcribe) → text only.
5. WhatsApp → Try-it page only, plus a recorded test-phone clip if it partly works. **Gate: if WhatsApp isn't echoing by the end of D4, cut it.**
6. The 2024–26 heat score → headline replays only.
7. Automatic flood-guide start → on request + urgent mode.
8. Agent-steps panel polish; mic button.
9. Model-tier cost optimisation (stay on Opus 5.5).

### 15.6 Judging period (Nov 5–27)
1. Daily health check; one person on call.
2. Fixes only on dev, never on the judging deployment.
3. Answer judge questions promptly.

---

## 16. Verification
1. **Unit tests** (CI, every PR):
   - heat rules incl. coastal humidity;
   - rain and flood thresholds;
   - shelter tool (3 nearest, no flood routes, "none near you" + PHC);
   - grouping; village confirmation; message cap; quiet hours.
2. **Event flows** (§5.2) on recorded data:
   - heat (warning, reminder, cancel);
   - dry spell;
   - river flood (prepare → flood watch → urgent);
   - heavy rain (city + slope wording);
   - official alert;
   - data-missing behaviour.
3. **Scenario suite** (§8.8.8): all 64 scenarios + prompt-injection tests against the deployed agents; output and trajectory scores; the bad-agent baseline scores clearly lower. Pass rate recorded; 0 unsafe messages allowed.
4. **Replays:** Kolhapur 2024, Vidarbha 2026, Kharghar 2023 produce timelines; the user checks them for correctness.
5. **Real phone, end to end:** consent sign-up in Marathi → heat warning template (job triggered manually) → 🔊 Listen → voice note → SHELTER → flood guide → urgent message → STOP → DELETE; plus a voice note in.
6. **Try-it page:**
   - works on a cheap Android phone;
   - replays work;
   - rate limit and spend cap trigger;
   - no WhatsApp sends from demo sessions.
7. **Load:** 20 parallel Try-it chats, no throttling errors.
8. **Ops:**
   - `cdk deploy` from a clean account;
   - budget alarm fires on a test threshold;
   - missed-scan alarm fires when the scan is disabled.
9. **Native speakers:** 30 Marathi/Hindi messages rated ≥ 4/5.
10. **Operational safety:**
    - the kill switch stops a test warning;
    - a correction message reaches the same recipients;
    - a stale shelter is replaced by "Call 1077".
11. **Data checks:**
    - CI fails on a shelter with a missing field or past its re-check date (§6.5);
    - CI fails on any number in the article or packs without a source-register row (§17).
12. **Deletion:** DELETE on a test number removes DynamoDB, S3 and AgentCore Memory records; verified by a script.

---

## 17. Source register and facts to verify
**Rule:** no statistic, threshold, helpline, shelter, or advisory appears in the app, packs, article, or video without a row in `docs/sources.csv`. CI checks this (§16).

**Each row records:**
- the claim;
- where it's used;
- publisher;
- URL (or document + page);
- licence / reuse terms;
- retrieval date;
- verification owner;
- status (unverified → verified).

The figures in §12 are unverified until they have rows. Where sources disagree we show the range and cite both.

**Items to register and verify**
| Item | Used in | Expected publisher | Owner | When |
|---|---|---|---|---|
| Helplines: 1077 (district), 108, 112, Kisan Call Centre 1800-180-1551 | Messages | NDMA / state govt / Ministry of Agriculture | User | Day 1 |
| IMD heat-wave definitions per region; heavy-rain categories | §5.2 thresholds | IMD | User | Day 2 |
| Heat, flood, drought advice steps | Skills, packs | IMD/KVK agromet, ICAR-CRIDA, NDMA, Maharashtra heat action plan | User | Day 2–3 |
| Shelters and cooling centers | Part 2 | District disaster plans, municipal lists (§6.5) | User | Day 1–3 |
| §12 disaster statistics (deaths, evacuations, deficits, temperatures) | Article, video, Try-it | IMD, state govt, NDMA, major news (2 sources each) | User | Day 3–6 |
| Agriculture Census figures | §13.3 | Ministry of Agriculture | User | Day 6 |
| Government cell-broadcast alerts in Maharashtra | §4.3 | NDMA / DoT | User | Day 2 |
| SACHET feed address and format | Flow 5 | NDMA | Prince | Day 2 |
| LGD access + open village-centre dataset (+ licences) | Village lookup | MoPR (LGD); dataset publisher | Prince | Day 2 |
| Open-Meteo non-commercial confirmation; CC BY 4.0 | Data | Open-Meteo | User | Day 0 |
| IMD content reuse terms | Article, app | IMD | User | Day 3 |
| Bedrock model IDs, AgentCore + Memory availability in Mumbai | Hosting, §10.2a | AWS | Prince | Day 0 |
| AgentCore Memory minimum event expiry; DynamoDB PITR window | §6.2 retention | AWS | Prince | Day 2 |
| Transcribe Marathi; Amazon Location walking routes in India | Voice, Part 2 | AWS | Prince | Day 2 |
| WhatsApp: test-number recipient limit, template rules, India fees | §5.1, cost | AWS / Meta | Prince | Day 0–2 |
| Sarvam terms and pricing | Marathi voice | Sarvam | User | Day 0 |
| ERA5 (gridded) normals vs IMD station normals: size of the cool bias and its effect on heat-wave detection (e.g. Akola mid-May ERA5 40.9°C vs IMD ~42–43°C) | Heat-wave rule, replays | IMD normals; our replay results | User + Claude | Day 2–6 |
| Which districts the sowing rule applies to (e.g. little rabi sowing in urban/coastal Konkan). **Oct 31: sowing check limited to kharif (monsoon) sowing; rabi left out: stored-moisture/irrigated sowing, "wait for rain" would fire daily** | Flow 2 | KVK / state agriculture calendar | User | Day 2 |
| ECMWF open data includes the 51-run ensemble (CC BY 4.0); Open-Meteo multi-location call weighting | §8.9 scale stage 3 | ECMWF; Open-Meteo | Prince | Day 3 |
| Nominatim usage policy (1 req/s, attribution) for dev; Amazon Location for production | §8.9 geocoding | OSMF; AWS | Prince | Day 2 |
| Coastal and hill cut-offs (distance to coast, elevation) matching IMD station types | §8.9 terrain | IMD | User | Day 2 |
| Excess Heat Factor method and percentiles (Nairn & Fawcett 2015; BoM) | Flow 1 (ours) | BoM / journal | User + Claude | Day 3 |
| GloFAS skill vs catchment size (supports the 1,000 m³/s large-river cut-off) | §8.9 river exposure | CEMS/GloFAS docs | Prince | Day 3 |
| Real cost per farmer | Article | Our AWS bill | Prince | Day 6 |

---

## 18. Repo layout
```
weatherwise/      all Python code, one package
  places/                any point -> state, district, grid cell, terrain, river (no village tables)
  risk/                  heat_wave (IMD, humid heat, Excess Heat Factor), heavy_rain, dry_spell, river_flood,
                         flood_guide_trigger, area_scan, recipient_groups, models
  weather/               Open-Meteo client, cell-cached WeatherService
  backtest/              backtest anywhere + verification scores
  shelters.py            Part 2 router      cap.py   CAP 1.2 alerts      cache.py   cache interface
  rules.py               loads rules/ + data/; serves message_policy
  mcp_server/            Climate Risk MCP server (6 tools) + ClimateRiskServices
  agents/                orchestrator, hooks, message_rules + steering (the Evaluator), warning_pipeline (Graph), delivery
  runtime.py             AgentCore Runtime entry point (chat + scheduled warning)
rules/                   what no API can give: global.toml (our rules), countries/in.toml (IMD rules,
                         helplines, seasons, quiet hours), languages/en|hi|mr.toml (safe messages, footer,
                         unsafe phrases). No state level; time zone from coordinates; language = person's choice
data/                    shelters_in.csv (verified shelters, district column), river_catchments_in.toml (pilot)
skills/                  SKILL.md procedures (heat, drought, flood prepare/urgent, shelter, sign-up)
evals/                   scenario suite + runner
tests/                   unit, snapshot (backtests) and live tests
scripts/                 developer tools (scan_today, backtest)
docs/                    planning-notes.md, build-log.md
```
Generated and private folders (`.venv/`, `cache/`, `evals/reports/`, `workshop_completion_evidence/`) are in `.gitignore`. The video project lives outside the repo.

---

## Appendix A: Test scenarios (the automated scenario suite)
**Status after all fixes:**
- **Test 1:** 12 pass, 2 honest limits.
- **Test 2:** 33 pass, 9 partial, 6 honest limits, 2 out of scope.

### A.1 Test 1: four village personas (14 cases)
**Personas**
- **P1 Rameshrao, 58:** rain-fed cotton, Beed; keypad phone; reads little.
- **P2 Sunita, 34:** farm labourer, Latur; son's smartphone.
- **P3 Patil family:** Kolhapur riverbank; cattle.
- **P4 Elderly couple:** Akola; keypad phone; son in Pune.

| # | Situation | Status | Covered by |
|---|---|---|---|
| 1 | P1 can't use WhatsApp | Limit | Village groups / family (§7) |
| 2 | P2 suspects a scam | Pass | Trusted introduction + footer |
| 3 | P2 must keep working in heat | Pass | Labourer steps (§4.1) |
| 4 | SHELTER in a village with no cooling center | Pass | "None near you" + PHC |
| 5 | Drought warning for a rain-fed farmer | Pass | Confidence + options |
| 6 | Dry spell, a little well water | Pass | Protective irrigation step |
| 7 | Flood forecast 2 days ahead | Pass | Prepare mode |
| 8 | Flood within hours, low battery | Pass | Urgent mode |
| 9 | Shelter route in a flood | Pass | No map routes |
| 10 | Network down during the flood | Limit | Send early (§7) |
| 11 | Low literacy | Pass | 🔊 Listen voice note |
| 12 | Can't share location | Pass | Typed/spoken village name |
| 13 | Too many warnings | Pass | Cap + confidence |
| 14 | Son wants warnings for parents | Pass | Family sign-up |

### A.2 Test 2: all regions (50 cases)
| # | Region | Situation | Part | Status |
|---|---|---|---|---|
| 1 | Konkan | Raigad hill village, extreme night rain | 3 | Pass (slope-safe) |
| 2 | Konkan | Ratnagiri fishing family, cyclone | 2 | Partial (outside pilot shelters) |
| 3 | Konkan | Sindhudurg humid coastal heat | 1 | Pass (humid-heat rule) |
| 4 | Konkan | Palghar Warli tribal village | all | Partial (language) |
| 5 | Konkan | Bhiwandi Hindi-speaking worker, heat | 2 | Pass |
| 6 | Konkan | Rice farmer, August dry spell | 1 | Pass |
| 7 | Konkan | Ambiguous village "Wadi" | 2 | Pass (confirmation) |
| 8 | Mumbai | Kurla family, extreme rain | 3 | Pass (city steps) |
| 9 | Mumbai | Stranded commuter | 2 | Pass (no routes; manholes warning) |
| 10 | Mumbai | Elderly person alone, humid heat | 2 | Pass |
| 11 | Mumbai | Hindi/Urdu worker, Dharavi | all | Pass |
| 12 | West | Kolhapur dam-release flood | 3 | Limit |
| 13 | West | Sangli family with cattle, flood ahead | 3 | Pass |
| 14 | West | Beed cane cutters in Kolhapur | 1/3 | Pass (location update) |
| 15 | West | Mahabaleshwar slopes, heavy rain | 3 | Pass |
| 16 | West | Solapur pomegranate, drought | 1 | Partial (fruit crops) |
| 17 | West | Pune elderly, heat wave | 2 | Pass |
| 18 | West | Kannada-speaking border farmer | all | Partial (machine-translated) |
| 19 | West | Dairy farmer, heat | 1 | Pass |
| 20 | West | Poultry farmer, heat | 1 | Pass |
| 21 | Marathwada | Tanker village, cattle starving | 1 | Pass |
| 22 | Marathwada | Latur heat during harvest | 1 | Pass |
| 23 | Marathwada | Telugu-speaking border farmer | all | Partial (machine-translated) |
| 24 | Marathwada | "Wadgaon" ambiguity | 1 | Pass |
| 25 | Marathwada | Nala flash flood | 3 | Limit |
| 26 | Marathwada | Woman farmer, husband's phone | 1 | Pass (several numbers per village) |
| 27 | Marathwada | Our warning vs government "normal" | 1 | Pass |
| 28 | Marathwada | Drip farmer, dry spell | 1 | Pass |
| 29 | Marathwada | Local crop names | 1 | Pass |
| 30 | Marathwada | Speech garbles village name | 1/2 | Pass |
| 31 | Vidarbha | Chandrapur 47°C labourer | 1 | Pass |
| 32 | Vidarbha | Akola couple, son registers | 1 | Pass |
| 33 | Vidarbha | Gadchiroli, no network, Gondi | all | Limit |
| 34 | Vidarbha | Melghat, no network | all | Limit |
| 35 | Vidarbha | Yavatmal distressed farmer, drought | 1 | Pass (tone + helpline) |
| 36 | Vidarbha | Nagpur orange, heat | 1 | Partial (fruit crops) |
| 37 | Vidarbha | Bhandara dam-release flood | 3 | Limit |
| 38 | Vidarbha | Warning would arrive at 2 am | 1 | Pass (quiet hours) |
| 39 | Vidarbha | Hailstorm | none | Out of scope |
| 40 | Vidarbha | Hindi-speaking Washim farmer | all | Pass |
| 41 | North | Jalgaon banana, 46°C | 1 | Partial (fruit crops) |
| 42 | North | Nashik grapes, cold wave | none | Out of scope |
| 43 | North | Nandurbar Bhil family | all | Partial (language) |
| 44 | North | Dhangar shepherd on the move | 1 | Partial (must update location) |
| 45 | North | Drought + canal rotation | 1 | Pass |
| 46 | North | Onion farmer, heat | 1 | Pass |
| 47 | System | Weather data down | all | Pass |
| 48 | System | One phone, 2 villages | 1 | Pass (up to 5 villages) |
| 49 | System | Pregnant worker, heat | 1 | Pass |
| 50 | System | Officer with 80 groups | all | Limit |
