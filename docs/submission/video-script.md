# WeatherWise video script (2:57)

Three minutes: why it matters, how the agents work, what it is built on and what comes next.
English only. Narrated by Amazon Polly (Amy, generative). Calm, soft wording: no alarm words, no "you are safe".

Built in Remotion (`weatherwise-video/`, outside this repo): one mp3 per line, so the picture follows the voice exactly.

---


### Scene 1 · The storms
**On screen:** Title card (also the thumbnail, ~3 s silent): logo, "Know early. Act early." and "AI weather alerts for farmers and families.", badge *Open source · Strands Agents on Amazon Bedrock AgentCore*, two phones (Mumbai heat, Bapatla flood steps). Then India's east coast (coastline only, no borders): Cyclone Arnab (Oct 28) and Cyclone Murasu (Nov 3) light up; *180,000+ people moved to safety*; an example official alert card and "So what do we do tonight?"

> This week, two cyclones reached India's east coast.
> More than a hundred and eighty thousand people were moved to safety.
> But a warning in colours and wind speeds doesn't tell a family what to do tonight.

### Scene 2 · The answer
**On screen:** The app slides in (Bapatla, then Mumbai); WeatherWise logo; the promise; the three parts.

> This is WeatherWise.
> Days of warning for farmers and families, before heat, dry spells or floods, with clear steps for what to do.

### Scene 3 · App tour
**On screen:** The real app on a phone: Mumbai heat → heatstroke → cooling places → Bapatla flood guide steps.

> Pick a place. Official warnings always come first.
> Below them, our own checks look a week ahead.
> Today in Mumbai, it's heat, so the app says what to do, and the signs of heatstroke.
> For shelter, it shows only checked places, or the helpline to call.
> And on the cyclone coast, an official alert has switched on the flood guide: one step at a time, and always, stay away from rivers, and never cross flowing water.

### Scene 4 · Agents
**On screen:** One diagram that builds as each piece is named: MCP server + data sources → Question → Orchestrator inside AgentCore Runtime → Warning / Flood Guide agents → Nova Pro → Evaluator. MCP is explained only here.

> Now, how it works.
> Every fact comes from our MCP server, in plain code, so the numbers can't be made up.
> Ask a question, and a Strands Orchestrator, running on Amazon Bedrock AgentCore, takes it.
> It calls those MCP tools, then hands off to a Warning agent or a Flood Guide agent, each with its own skills.
> The model is Amazon Nova, on Bedrock.
> Before you see a word, an Evaluator checks the draft in code: helplines present, no made-up numbers, never "you are safe".
> If it fails, the agent writes it again.

### Scene 5 · Pipeline
**On screen:** Strands Graph boxes + AgentCore Memory; the live /impact page; the real trace from AgentCore Observability.

> The same agents run our warning pipeline: a Strands Graph that AgentCore starts every morning at three.
> Today it covers twenty-five places, from the cyclone coast to the drought belts.
> AgentCore Memory recalls what it said yesterday, so it writes an update, not a repeat.
> Every step is traced in AgentCore Observability.

### Scene 6 · Stack
**On screen:** The agent pieces in one band (already named), then only the new ones: EventBridge, ECS Fargate, S3, CloudFormation, GitHub Actions.

> Around them: EventBridge, ECS Fargate and S3, in one CloudFormation stack, deployed by GitHub Actions.

### Scene 7 · Proof
**On screen:** Four cards: 0 unsafe (78 warnings, 7 real disasters) · 9 days · $0.25 · misses published.

> And we tested it on the real model.
> Seven real disasters, seventy-eight warnings, and not one unsafe message got through.
> Kolhapur's floods, replayed: nine days of warning.
> The whole test cost twenty-five cents. And we publish our misses.

### Scene 8 · Live and next
**On screen:** Live today (checklist) | Next: rules/countries/in.toml, + Africa, + text messages.

> WeatherWise is live today, and runs every morning on its own.
> Nothing in the code is tied to India. A new country is one rules file, so Africa is next, along with text messages to families.

### Scene 9 · Close
**On screen:** The map comes back with all 25 watched places lighting up; then the end card: weatherwise.online, GitHub, "Built with Strands Agents on Amazon Bedrock AgentCore", both team photos.

> The next time a storm reaches the coast, a family won't just hear that it's coming.
> They'll know what to do, days ahead, in words they understand.

---

## Facts behind each line
| Line | Source |
|---|---|
| Arnab, landfall Oct 28, 2026; 180,000+ moved to safety (AP + Odisha) | [NBC News](https://www.nbcnews.com/world/asia/india-evacuates-180000-cyclone-arnab-hits-coast-rcna606057), [The Week](https://www.theweek.in/news/india/2026/10/28/cyclone-arnab-makes-landfall-andhra-pradesh.html) |
| Murasu, landfall Nov 3, 2026, south Andhra coast | [Al Jazeera](https://www.aljazeera.com/news/2026/11/3/cyclone-murasu-makes-landfall-on-indias-eastern-coast), [The Week](https://www.theweek.in/news/india/2026/11/03/cyclone-murasu-landfall-andhra-pradesh.html) |
| Orchestrator → warning_agent / flood_guide_agent, skills, Evaluator | `weatherwise/agents/orchestrator.py`, `steering.py` |
| Graph: risk check → writer → safety gate → delivery rules; Memory | `weatherwise/agents/warning_pipeline.py`, `place_memory.py` |
| 25 places, 3 drafts sent back, $0.066 | Morning run 2026-11-04 03:00 IST, `/api/daily` |
| Stack | `infra/cloudformation/weatherwise-service.yaml`, `.github/workflows` |
| 78 warnings, 7 real disasters, 0 unsafe got through, $0.25 | `evals/results/` real-model eval (Nova Pro), PR #53 |
| A country is one rules file | `rules/countries/in.toml`; no place names in code |
| 25 watched places on the closing map | `data/daily_watch.toml` |
| Kolhapur 9 days | `evals/results/REPLAYS.md` |

Death counts are left out on purpose: the sources disagree. Messages are not yet sent to anyone; the script says so.
