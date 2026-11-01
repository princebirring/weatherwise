# WeatherWise: deployment to-do for DevOps

**For:** Prince, and the Claude Code session he runs this with.
**Goal:** first place. Start with "Do this first" below. The result is a public HTTPS link judges
can open, with live chat on Claude in Amazon Bedrock and the agents on Amazon Bedrock AgentCore,
in one AWS region of Prince's choice, using only the six services listed in "The stack".
**Deadline:** judging deployment frozen **Nov 3, 6 PM IST** (submission Nov 4).

> **To the Claude session reading this:** work through the phases in order and tick the boxes.
> Each step has a check; do not move on until it passes. Ask Prince before anything that costs
> money beyond what is listed, adds an AWS service not listed under "The stack", or changes the
> AWS account outside this project. Do not edit `rules/` or `skills/` (safety text and official
> thresholds): if a step seems to need it, stop and ask Prashant.

---

## Do this first: what we need to win (reviewed Oct 31 against the 12 entries posted)

**Where we stand.** On ideas we lead: we're the only entry that covers all three parts of AWS's
climate-resilience example, and the only one that replays real past disasters (Kolhapur flood
2024: 9 days of warning). On proof we're behind: the two strongest rival entries both run their
Strands agents live on Bedrock + AgentCore, publish test results measured against the real model,
and include a table showing results *with and without* their safety check. Our agents have
**never run on Bedrock**. Judges score technical execution at 25%, so this is the gap that loses
us first place. Everything below closes it, in order.

| # | Who | By (IST) | Task |
|---|---|---|---|
| W1 | Prince | **Nov 1, 12 PM** | Bedrock access + a key for Prashant's laptop |
| W2 | Prince | Nov 1, 6 PM | Run the scenario suite on the real model once |
| W3 | Prince | Nov 2 | Phase 1 live link (below) |
| W4 | Prince | Nov 3, 12 PM | Phase 2 on AgentCore + capture the evidence |
| W5 | Claude (Prashant's session) | after W1 | Evaluator on/off comparison, Limits section, article, video |

- [ ] **W1. Bedrock access today.** This blocks everything else.
  1. In the Bedrock console in `<region>`, enable **Claude Sonnet 5.5**. If it is offered only
     through an inference profile, prefer the **global** profile (cheapest; we store no personal
     data, so where the model runs does not matter). Note the **inference-profile ID** (decision 0.1).
  2. Create an IAM user (or an SSO permission set) for Prashant with **only**
     `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on that profile and the
     foundation models behind it. Share the keys privately, never in the repo or chat logs. This
     lets Claude run the agents and the comparison (W5) locally while you deploy.
  3. Set the AWS Budget alarms (decision 0.3).
  **Check:**
  ```bash
  aws bedrock-runtime converse --region <region> --model-id <profile-id> \
    --messages '[{"role":"user","content":[{"text":"Say OK"}]}]'
  ```
  answers, and from the repo `CLIMATE_AGENT_MODEL_ID=<profile-id> AWS_REGION=<region> uv run python -m weatherwise.api.server`
  then `curl localhost:8080/api/status` shows `"agents_ready": true`.

- [ ] **W2. First real-model scenario run** (30 cases, a few dollars at most):
  ```bash
  CLIMATE_AGENT_MODEL_ID=<profile-id> AWS_REGION=<region> uv run python evals/run_scenarios.py --judge
  ```
  The report is written to `evals/reports/`. Commit it on a branch and open a PR. **Don't fix
  failures yourself:** send the report to Prashant; Claude fixes them on his side (prompts and
  skills, not `rules/`).
  **Check:** the report exists and lists a pass rate for each part (heat/drought, shelter, flood).

- [ ] **W3. Live public link by Nov 2:** Phase 1 below. Judges click links: the two strongest
  rivals both have one.

- [ ] **W4. AgentCore + evidence by Nov 3, 12 PM:** Phase 2 below, then capture these for the
  video and article (send them to Prashant):
  1. **A screenshot of an AgentCore observability trace** (or the CloudWatch GenAI view) of one
     Marathi chat ("उद्या अकोल्यात खूप ऊन असेल का?"), showing the Orchestrator → specialist →
     Evaluator steps and the MCP tool calls.
  2. **Timings from the public URL** (run after the 1.7 warm-up):
     ```bash
     U=https://<service-url>
     for i in 1 2 3 4 5; do curl -s -o /dev/null -w "today %{time_total}s\n" "$U/api/place?lat=20.71&lon=77.00"; done
     ```
     plus five chat timings from the browser network tab (`/api/chat`).
  3. **Cost per chat answer:** input and output tokens for 10 chats (CloudWatch Bedrock
     invocation metrics) multiplied by the model price, in US$ per answer.
  4. **The architecture as deployed:** a list of the AWS resources actually created (ECS service
     and its load balancer, ECR repository, AgentCore Runtime, IAM roles, log groups, Budgets), so
     the diagram in the article is exactly what runs.

- [ ] **W5. (Claude, not Prince.)** Once W1 works: add an "Evaluator off" switch to
  `evals/run_scenarios.py` and publish the side-by-side table (unsafe or wrong advice caught with
  vs without the Evaluator); add a "Limits" section to the README (for example: the 2024 Wayanad
  landslide is missed, and we don't model cyclone wind); write the Builder Center article and
  record the video with W4's evidence.

---

## The stack: six services, nothing else for judging

Fewer services that all work beat many half-done ones. **Do not add CloudFront, WAF, DynamoDB,
S3, Lambda, EventBridge, SQS, NAT Gateway or Route 53 for judging** (see Phase 3 for later).

| AWS service | Its one job |
|---|---|
| **Amazon Bedrock** | Claude Sonnet 5.5: the model behind the chat agents |
| **Bedrock AgentCore Runtime** | Runs the Strands agents (Orchestrator → Warning / Flood Guide → Evaluator) |
| **Amazon ECS (Express Mode, Fargate) + ECR** | Runs the one container: website + facts API (HTTPS link and load balancer come with Express Mode); ECR stores the image |
| **Amazon CloudWatch** | Logs, traces, token counts (the evidence for W4) |
| **IAM** | The two roles (container, AgentCore) and Prashant's Bedrock-only key |
| **AWS Budgets** | Cost alarms on the personal account |

**Why no CloudFront / WAF:** the only thing that costs money per request is chat, and the code
already caps it: 6 chats a minute per visitor and **100 a day in total**
(`WEATHERWISE_CHATS_PER_DAY`). Past the cap the site says "demo busy" and everything else keeps
working. Worst case about US$10 a day in model cost.

**Why the split:** the container answers Today / Safe place / flood guide / replays with plain,
tested code via our MCP server (fast, cheap, checkable). Only the Ask chat uses the agents on
AgentCore. "AI only where it helps; checked code everywhere else."

### Expected cost (US$, before any GST)

| Item | Per month |
|---|---|
| Fargate, 1 vCPU / 2 GB, always on (ARM64; x86 about 38) | ≈ 22–38 |
| Load balancer (comes with Express Mode) + public IPv4 addresses | ≈ 30 |
| ECR, CloudWatch logs and traces, AgentCore Runtime at demo traffic | ≈ 2–5 |
| **Fixed total** | **≈ 55–75** |
| Claude Sonnet 5.5 (global profile $2 / $10 per million tokens; India/Asia profile +10%) | ≈ $0.10 per chat answer; ≈ $20 for W2/W5 testing, ≈ $30 for judging |

November in all: **≈ US$110–130, ≈ US$130–155 with GST.** Confirm the rates in the AWS Pricing
Calculator for the chosen region. New accounts usually get up to US$200 in credits (decision 0.4).
After judging, stopping the ECS service (which removes the load balancer) brings the cost to
about zero.

---

## 0. What you are deploying

```
Browser ──HTTPS──> ECS Express Mode load balancer
                         │
                         ▼
          ┌─────────── one container (Dockerfile) ───────────┐
          │ WeatherWise API  weatherwise/api   (port 8080)   │
          │   serves the website (website/dist) and /api/*   │
          │   starts the Climate Risk MCP server as a local  │
          │   process (stdio) for every fact                 │
          │   chat: Strands agents, Claude on Bedrock        │
          └───────────────────────────────────────────────────┘
                         │ (Phase 2: chat goes to AgentCore instead)
                         ▼
          AgentCore Runtime: weatherwise/runtime.py (agents + same MCP server inside)
```

- **Region:** one region for everything, Prince's choice: it must offer Claude on Bedrock, AgentCore Runtime and
  ECS Express Mode. The code reads `AWS_REGION`; below, `<region>` stands for it.
- **No database is needed.** Nothing personal is stored; chat sessions live in memory for 24 h,
  which is why the service runs exactly **one** task (a second task would not know the first
  one's chat sessions).
- **Data sources** are public and need no AWS setup: SACHET (official warnings, NDMA), Open-Meteo
  (forecasts, river flow, history), OpenStreetMap Nominatim (place names), Natural Earth (coastline,
  baked into the image). The service needs outbound HTTPS to `sachet.ndma.gov.in`, `*.open-meteo.com`,
  `nominatim.openstreetmap.org` and the Overpass mirrors.

### Settings (environment variables)

| Variable | Value | What it does |
|---|---|---|
| `CLIMATE_AGENT_MODEL_ID` | the inference-profile ID from the Bedrock console | Turns chat on. Without it the site works, chat says "not connected yet" |
| `AWS_REGION` | `<region>` | Bedrock region |
| `WEATHERWISE_CACHE_DIR` | `/tmp/weatherwise` (already set in the Dockerfile) | Writable folder for downloaded forecasts |
| `WEATHERWISE_GEODATA_DIR` | `/app/geodata` (already set) | Coastline file baked into the image |
| `WEATHERWISE_CHATS_PER_DAY` | `100` (the default) | Daily chat cap: the AI-spend guard |
| `WEATHERWISE_CHATS_PER_MINUTE` | `6` (the default) | Per visitor |
| `WEATHERWISE_TRUSTED_PROXY_HOPS` | `1` | The load balancer adds one `X-Forwarded-For` entry; the per-visitor limit reads only that one, so visitors can't fake it |
| `WEATHERWISE_BEHIND_CLOUDFRONT` | **leave unset** | Only for a future CloudFront setup (Phase 3) |
| `OPEN_METEO_API_KEY` | optional (decision 0.2) | Uses Open-Meteo's paid hosts with their own rate limit |
| `CLIMATE_RISK_MCP_URL` | **leave unset** | Points at a shared, deployed MCP server (Phase 3) |

### Decisions to make with Prashant before starting

- [ ] **0.1 Model:** Claude Sonnet 5.5 in `<region>`; send back the inference-profile ID.
- [ ] **0.2 Open-Meteo key:** the free API is shared and rate-limited. When it says "too many requests" our code waits 5 / 10 / 20 / 40 s, so a busy judging day can make a first visit to a new village take over a minute (measured Oct 31). A paid key (from about €29/month) removes this. Decide yes/no.
- [ ] **0.3 Budget alarms:** US$50 and US$100 per month, emails to Prince and Prashant.
- [ ] **0.4 Billing check:** under Billing → Tax settings, see whether the account is billed by AWS India (AISPL, in INR, +18% GST), and whether the new-account credits are on it. On the "Free" account plan, upgrade to "Paid" to use Bedrock and AgentCore (credits carry over).

---

## Phase 1: one container live on a public HTTPS link (do first, target Nov 2)

- [ ] **1.1 Build the image.** Built and smoke-tested on Oct 31 with Podman on an Apple-silicon Mac (arm64, 421 MB), and CI builds the linux/amd64 image on every pull request. **Use arm64 (Graviton): cheaper on Fargate and builds natively on an Apple-silicon Mac.** If Express Mode doesn't offer ARM64, build amd64 on an x86 machine instead (emulated amd64 builds on Apple silicon crash inside the Python installer).
  ```bash
  docker build -t weatherwise .
  docker run --rm -p 8080:8080 weatherwise
  ```
  The build runs the website tests before building it. If the coastline download step fails, retry: it fetches a pinned Natural Earth release from GitHub.
  **Check:** `curl localhost:8080/api/status` → `{"agents_ready": false, ...}`; open `http://localhost:8080/app` and `http://localhost:8080/`.

- [ ] **1.2 Run the test suites once** (from the repo, not the image):
  ```bash
  uv sync && uv run pytest -m "not live"      # expect 232 passed
  uv run pytest -m live                        # real APIs; expect all passed
  ```

- [ ] **1.3 Bedrock from the container.** With local AWS credentials,
  `docker run --rm -p 8080:8080 -e CLIMATE_AGENT_MODEL_ID=<id> -e AWS_REGION=<region> -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN weatherwise`
  **Check:** `/api/status` shows `"agents_ready": true`, and asking "Will it be very hot?" on `/app/ask` gets a reply with "How this answer was made" steps.

- [ ] **1.4 Push to ECR** in `<region>` (repository `weatherwise`, image tag = git commit SHA, plus `judging` for the frozen one).

- [ ] **1.5 Run it on ECS Express Mode** in `<region>` (AWS's replacement for App Runner, which no longer accepts new accounts). Create the service from the ECR image:
  - Port 8080; health check path `/api/status`.
  - 1 vCPU, 2 GB, ARM64 (or x86, matching 1.1). **Exactly 1 task: minimum 1, maximum 1** (one warm task keeps the forecast cache and the chat sessions; see 1.7).
  - Task role: `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on the chosen inference profile and the foundation models behind it. Nothing else.
  - Networking: tasks in **public subnets with a public IP**, so they reach the internet with **no NAT Gateway** (a NAT Gateway alone would add about US$33/month).
  - Environment: the values from the settings table, including `WEATHERWISE_TRUSTED_PROXY_HOPS=1`.
  - Logs: CloudWatch, retention 14 days.
  - If Express Mode is not offered in `<region>`: a plain ECS service on Fargate behind an Application Load Balancer with an ACM certificate, same image and settings.

- [ ] **1.6 Smoke test the public URL.** All must pass:
  ```bash
  U=https://<service-url>
  curl -s $U/api/status                                              # agents_ready: true
  curl -s "$U/api/places?q=Akola" | head -c 200                      # candidates in Maharashtra
  curl -s "$U/api/place?lat=16.70&lon=74.24" | head -c 200           # Kolhapur: place + outlook
  curl -s -o /dev/null -w "%{http_code}\n" "$U/api/place?lat=-0.10&lon=34.75"   # Kenya: 422 (not covered)
  curl -s "$U/api/shelters?lat=16.70&lon=74.24&hazard=flood" | head -c 200      # never a route
  curl -s -o /dev/null -w "%{http_code}\n" $U/app/shelter            # 200 (website screens)
  curl -s "$U/api/official?lat=17.38&lon=78.48" | head -c 200         # status "ok" (not "unavailable")
  ```
  Then in a phone browser: `/app` → choose मराठी → search "Akola" → Today → Safe place → Help; switch language in the header (every word changes); `/` → the four replays show charts.

- [ ] **1.7 Warm the cache right after each deploy.** A new 25 km forecast area takes several seconds the first time (it also fetches its 30-year rain history once and 30 days of past forecasts each day, for the unusual-rain line and the forecast correction; much longer if Open-Meteo is rate-limiting); the replays take 5–35 s the first time. Run once:
  ```bash
  for id in kolhapur_flood_2024_07 vijayawada_flood_2024_08 vidarbha_heat_2026_04 kharghar_heat_2023_04; do curl -s -o /dev/null -w "$id %{time_total}s\n" $U/api/replays/$id; done
  for p in "16.70&lon=74.24" "20.71&lon=77.00" "19.03&lon=73.07" "25.59&lon=85.14" "18.40&lon=76.56"; do curl -s -o /dev/null -w "%{time_total}s\n" "$U/api/place?lat=$p"; done
  ```
  **Check:** a second run of both loops answers in under 1 s each.

- [ ] **1.8 Cost guard.** Budget alarms (0.3) are on. `WEATHERWISE_CHATS_PER_DAY` (100) caps chat; when hit, the site says "demo busy" and everything except chat keeps working.
  **Check:** set `WEATHERWISE_CHATS_PER_MINUTE=1` briefly and send two chats: the second is refused (429); set it back to 6. Then send two chats with a made-up `X-Forwarded-For: 1.2.3.4` header: the second is still refused.

- [ ] **1.9 Send Prashant:** the URL, region, model ID, and the image tag running.

---

## Phase 2: agents on AgentCore (target Nov 3, 12 PM)

- [ ] **2.1 Deploy the agent runtime to AgentCore Runtime** in `<region>`, the same way as workshop Module 5 (`agentcore configure` with entry point `weatherwise/runtime.py`, then `agentcore launch`). We don't use AgentCore Evaluations or Policy, so any region with AgentCore Runtime works.
  - The package must include `weatherwise/`, `rules/`, `data/`, `skills/` (the agents read skills and the MCP server reads rules and data). If the toolkit wants a requirements file: `uv export --no-dev --no-hashes > requirements.txt`.
  - Environment: `CLIMATE_AGENT_MODEL_ID`, `AWS_REGION`, `WEATHERWISE_CACHE_DIR=/tmp/weatherwise`. Leave `CLIMATE_RISK_MCP_URL` unset: the runtime starts the MCP server inside its own microVM.
  - Execution role: Bedrock invoke (as 1.5) plus what AgentCore needs for logs and traces.
  **Check:** invoke with `{"type": "chat", "session_id": "<36+ char uuid>", "message": "Will it be very hot in Akola this week?", "country": "in", "language": "en"}` → `text`, `steps`, `violations: []`. Invoke with `"language": "mr"` → the reply is in Marathi.

- [ ] **2.2 Code task (Claude, in this repo), so website chat goes through AgentCore:** add an optional setting `WEATHERWISE_AGENT_RUNTIME_ARN` to `weatherwise/api/server.py`. When set, `team_factory` is replaced by a call to AgentCore `invoke_agent_runtime` with the runtime's `chat` payload (see the docstring of `weatherwise/runtime.py`), returning the same `{text, used_fallback, violations, steps}`. Keep the in-process path when unset. Add a test with a fake client in `tests/test_api.py`. Then redeploy the container with the ARN and give its task role `bedrock-agentcore:InvokeAgentRuntime` on that runtime.
  **Check:** a chat on the website shows up in the AgentCore observability / CloudWatch traces.

- [ ] **2.3 Freeze the judging deployment** at Nov 3, 6 PM: tag the image `judging`, pin the service to it, no deploys after that except agreed hot-fixes.

---

## Phase 3: after judging only (do not start before Phase 1 and 2 pass)

Each needs agreement with Prashant, and most need code work first (Claude, in this repo):

- [ ] **3.1 CloudFront + WAF in front of the load balancer**, before real farmers use it: faster pages on slow connections, and bad traffic blocked before it reaches us. Set `WEATHERWISE_BEHIND_CLOUDFRONT=1`, forward the `CloudFront-Viewer-Address` header, unset `WEATHERWISE_TRUSTED_PROXY_HOPS`, and make the load balancer accept only CloudFront.
- [ ] **3.2 Flood-guide memory in the live service.** Replays keep the guide on until 7 quiet mornings (`stay_on_quiet_days`); the live service has no memory yet. Code: a small "active events" store (DynamoDB table `weatherwise-active-events`, key = forecast cell, value = last flood-signal date) used with `keep_guide_on` in `weatherwise/risk/flood_guide_trigger.py`.
- [ ] **3.3 Shared forecast cache** (S3 or DynamoDB) behind the `Cache` interface in `weatherwise/cache.py`, so more than one task can run and Lambda becomes an option.
- [ ] **3.4 Shared MCP server** on AgentCore Runtime (MCP protocol, `--http --host 0.0.0.0 --port 8000`, path `/mcp`) behind AgentCore Gateway with auth; then set `CLIMATE_RISK_MCP_URL` and add auth headers to `climate_risk_client()` in `weatherwise/agents/orchestrator.py`.
- [ ] **3.5 The 6 AM warning job:** EventBridge Scheduler → Lambda that groups subscribers with `recipient_groups_for_area` (`weatherwise/risk/recipient_groups.py`) and invokes the runtime with `{"type": "warning", "group": ...}`; DynamoDB ledger and SQS outbox replace the in-memory ones in `weatherwise/agents/delivery.py`. Only meaningful with WhatsApp.
- [ ] **3.6 WhatsApp** (AWS End User Messaging Social): only if it passes the Day 4 gate in the plan.
- [ ] **3.7 Amazon Location** for place search and names in production (Nominatim's public service allows 1 request/s).

---

## Things that must stay true (check after every deploy)

- Places outside India say "not covered yet" and show **no Indian helpline numbers** (Kenya check in 1.6).
- `/api/official` answers `"status": "ok"`. If it says `"unavailable"`, SACHET cannot be reached from AWS: fix the network path before judging.
- Flood shelter answers **never** contain a map route (`directions_link` is null for floods).
- The site states "Not an official warning service. Always follow IMD." and 112 / 108 / 1077 are one tap away.
- No personal data in logs: the API logs no message text or locations; keep CloudWatch retention short.
