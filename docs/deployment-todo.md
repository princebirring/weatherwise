# WeatherWise: deployment to-do for DevOps

**For:** Prince, and the Claude Code session he runs this with.
**Goal:** a public HTTPS link judges can open, with live chat on Claude in Amazon Bedrock and the
agents on Amazon Bedrock AgentCore.
**Deadline:** judging deployment frozen **Nov 3, 6 PM IST** (submission Nov 4).

> **To the Claude session reading this:** work through the phases in order and tick the boxes.
> Each step has a check; do not move on until it passes. Ask Prince before anything that costs
> money beyond what is listed, or changes the AWS account outside this project. Do not edit
> `rules/` or `skills/` (safety text and official thresholds): if a step seems to need it, stop
> and ask Prashant.

---

## 0. What you are deploying

```
Browser ──HTTPS──> [CloudFront + WAF]  (Phase 2)
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

- **Region:** `ap-south-1` (Mumbai) unless Bedrock model access forces another; the code reads `AWS_REGION`.
- **No database is needed for Phase 1.** Nothing personal is stored; chat sessions live in memory for 24 h.
- **Data sources** are public and need no AWS setup: Open-Meteo (forecasts, river flow, history),
  OpenStreetMap Nominatim (place names), Natural Earth (coastline, baked into the image).

### Settings (environment variables)

| Variable | Phase 1 value | What it does |
|---|---|---|
| `CLIMATE_AGENT_MODEL_ID` | the inference-profile ID from the Bedrock console (e.g. `apac.anthropic.claude-…`) | Turns chat on. Without it the site works, chat says "not connected yet" |
| `AWS_REGION` | `ap-south-1` | Bedrock region |
| `WEATHERWISE_CACHE_DIR` | `/tmp/weatherwise` (already set in the Dockerfile) | Writable folder for downloaded forecasts |
| `WEATHERWISE_GEODATA_DIR` | `/app/geodata` (already set) | Coastline file baked into the image |
| `WEATHERWISE_CHATS_PER_DAY` | `500` | Daily chat cap: the AI-spend guard |
| `WEATHERWISE_CHATS_PER_MINUTE` | `6` | Per visitor |
| `WEATHERWISE_TRUSTED_PROXY_HOPS` | `1` on App Runner; leave unset behind CloudFront | How the per-visitor limit finds the real visitor address. Never trust `X-Forwarded-For` blindly |
| `OPEN_METEO_API_KEY` | optional (decision 0.2) | Uses Open-Meteo's paid hosts with their own rate limit |
| `CLIMATE_RISK_MCP_URL` | **leave unset** in Phase 1 | Points at a shared, deployed MCP server (Phase 3) |

### Decisions to make with Prashant before starting

- [ ] **0.1 Model:** which Claude model / inference profile is enabled in the account and region. Send the ID back.
- [ ] **0.2 Open-Meteo key:** the free API is shared and rate-limited. When it says "too many requests" our code waits 5 / 10 / 20 / 40 s, so a busy judging day can make a first visit to a new village take over a minute (measured Oct 31). A paid key (from about €29/month) removes this. Decide yes/no.
- [ ] **0.3 Budget:** the monthly amount for the AWS Budget alarm (suggest US$50) and who gets the email.

---

## Phase 1: one container live on a public HTTPS link (do first, target Nov 2)

- [ ] **1.1 Build the image.** Built and smoke-tested on Oct 31 with Podman on an Apple-silicon Mac (arm64, 421 MB), and CI now builds the linux/amd64 image on every pull request. Build the amd64 image on an x86 machine or in CI: emulated amd64 builds on Apple silicon crash inside the Python installer (qemu segfault).
  ```bash
  docker build -t weatherwise .
  docker run --rm -p 8080:8080 weatherwise
  ```
  The build runs the website tests before building it. If the coastline download step fails, retry: it fetches a pinned Natural Earth release from GitHub.
  **Check:** `curl localhost:8080/api/status` → `{"agents_ready": false, ...}`; open `http://localhost:8080/app` and `http://localhost:8080/`.

- [ ] **1.2 Run the test suites once** (from the repo, not the image):
  ```bash
  uv sync && uv run pytest -m "not live"      # expect 168 passed
  uv run pytest -m live                        # real APIs; expect all passed
  ```

- [ ] **1.3 Bedrock access.** Enable the chosen Claude model in the region; note the inference-profile ID (0.1).
  **Check:** with local AWS credentials,
  `docker run --rm -p 8080:8080 -e CLIMATE_AGENT_MODEL_ID=<id> -e AWS_REGION=ap-south-1 -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN weatherwise`
  then `/api/status` shows `"agents_ready": true`, and asking "Will it be very hot?" on `/app/ask` gets a reply with "How this answer was made" steps.

- [ ] **1.4 Push to ECR** (repository `weatherwise`, image tag = git commit SHA, plus `judging` for the frozen one). App Runner runs linux/amd64: build on x86 (or GitHub Actions), not emulated on Apple silicon.

- [ ] **1.5 Run it on AWS App Runner** (recommended: one container, HTTPS URL included, no load balancer to manage). Check App Runner is offered in the chosen region; if not, use ECS Fargate behind an ALB with the same image and settings.
  - Port 8080; health check `HTTP /api/status`.
  - CPU 1 vCPU, memory 2 GB. **Min instances 1, max 2.** Keeping one instance warm keeps the forecast cache warm (see 1.7).
  - Instance role: `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on the chosen inference profile and the foundation models behind it. Nothing else.
  - Environment: the Phase 1 values from the table, `WEATHERWISE_TRUSTED_PROXY_HOPS=1`.
  - Logs: CloudWatch, retention 14 days.

- [ ] **1.6 Smoke test the public URL.** All must pass:
  ```bash
  U=https://<service-url>
  curl -s $U/api/status                                              # agents_ready: true
  curl -s "$U/api/places?q=Akola" | head -c 200                      # candidates in Maharashtra
  curl -s "$U/api/place?lat=16.70&lon=74.24" | head -c 200           # Kolhapur: place + outlook
  curl -s -o /dev/null -w "%{http_code}\n" "$U/api/place?lat=-0.10&lon=34.75"   # Kenya: 422 (not covered)
  curl -s "$U/api/shelters?lat=16.70&lon=74.24&hazard=flood" | head -c 200      # never a route
  curl -s -o /dev/null -w "%{http_code}\n" $U/app/shelter            # 200 (website screens)
  ```
  Then in a phone browser: `/app` → choose मराठी → search "Akola" → Today → Safe place → Help; switch language in the header (every word changes); `/` → the three replays show charts.

- [ ] **1.7 Warm the cache right after each deploy.** A new 25 km forecast area takes ~6 s the first time (much longer if Open-Meteo is rate-limiting); the replays take 5–35 s the first time. Run once:
  ```bash
  for id in kolhapur_flood_2024_07 vidarbha_heat_2026_04 kharghar_heat_2023_04; do curl -s -o /dev/null -w "$id %{time_total}s\n" $U/api/replays/$id; done
  for p in "16.70&lon=74.24" "20.71&lon=77.00" "19.03&lon=73.07" "25.59&lon=85.14" "18.40&lon=76.56"; do curl -s -o /dev/null -w "%{time_total}s\n" "$U/api/place?lat=$p"; done
  ```
  **Check:** a second run of both loops answers in under 1 s each.

- [ ] **1.8 Cost guard.** AWS Budget alarm (0.3). `WEATHERWISE_CHATS_PER_DAY` caps chat; when hit, the site says "demo busy" and everything except chat keeps working.
  **Check:** set `WEATHERWISE_CHATS_PER_MINUTE=1` briefly and send two chats: the second is refused (429); set it back to 6.

- [ ] **1.9 Send Prashant:** the URL, region, model ID, and the image tag running.

---

## Phase 2: agents on AgentCore, CloudFront + WAF (target Nov 3, 12 PM)

- [ ] **2.1 Deploy the agent runtime to AgentCore Runtime**, the same way as workshop Module 5 (`agentcore configure` with entry point `weatherwise/runtime.py`, then `agentcore launch`).
  - The package must include `weatherwise/`, `rules/`, `data/`, `skills/` (the agents read skills and the MCP server reads rules and data). If the toolkit wants a requirements file: `uv export --no-dev --no-hashes > requirements.txt`.
  - Environment: `CLIMATE_AGENT_MODEL_ID`, `AWS_REGION`, `WEATHERWISE_CACHE_DIR=/tmp/weatherwise`. Leave `CLIMATE_RISK_MCP_URL` unset: the runtime starts the MCP server inside its own microVM.
  - Execution role: Bedrock invoke (as 1.5) plus what AgentCore needs for logs and traces.
  **Check:** invoke with `{"type": "chat", "session_id": "<36+ char uuid>", "message": "Will it be very hot in Akola this week?", "country": "in", "language": "en"}` → `text`, `steps`, `violations: []`. Invoke with `"language": "mr"` → the reply is in Marathi.

- [ ] **2.2 Code task (Claude, in this repo), so website chat goes through AgentCore:** add an optional setting `WEATHERWISE_AGENT_RUNTIME_ARN` to `weatherwise/api/server.py`. When set, `team_factory` is replaced by a call to AgentCore `invoke_agent_runtime` with the runtime's `chat` payload (see the docstring of `weatherwise/runtime.py`), returning the same `{text, used_fallback, violations, steps}`. Keep the in-process path when unset. Add a test with a fake client in `tests/test_api.py`. Then redeploy the container with the ARN and give its role `bedrock-agentcore:InvokeAgentRuntime` on that runtime.
  **Check:** a chat on the website shows up in the AgentCore observability / CloudWatch traces.

- [ ] **2.3 CloudFront in front of App Runner,** with AWS WAF:
  - Behaviours: `/api/*`: no caching, all methods, forward query strings; `/assets/*`: cache long (file names are hashed); default (`/`, `/app/*`): cache 5 min.
  - Origin request policy must forward the **`CloudFront-Viewer-Address`** header (the API uses it to tell visitors apart), and then **unset** `WEATHERWISE_TRUSTED_PROXY_HOPS` on the container.
  - WAF: AWS managed common rule set; a rate-based rule on `/api/chat` (e.g. 100 requests / 5 min per IP).
  - Restrict the origin so the App Runner URL is not used directly (custom header shared secret checked by WAF, or an origin access setup).
  **Check:** the 1.6 smoke test passes on the CloudFront URL; the rate-based rule blocks a burst on `/api/chat`.

- [ ] **2.4 Freeze the judging deployment** at Nov 3, 6 PM: tag the image `judging`, pin the service to it, no deploys after that except agreed hot-fixes.

---

## Phase 3: after judging, or only if time allows (do not start before Phase 1 and 2 pass)

Each needs code work first (Claude, in this repo) and agreement with Prashant:

- [ ] **3.1 Flood-guide memory in the live service.** Replays keep the guide on until 7 quiet mornings (`stay_on_quiet_days`); the live service has no memory yet. Code: a small "active events" store (DynamoDB table `weatherwise-active-events`, key = forecast cell, value = last flood-signal date) used with `keep_guide_on` in `weatherwise/risk/flood_guide_trigger.py`.
- [ ] **3.2 Shared forecast cache** (S3 or DynamoDB) behind the `Cache` interface in `weatherwise/cache.py`, so all instances share one warm cache and Lambda becomes an option.
- [ ] **3.3 Shared MCP server** on AgentCore Runtime (MCP protocol, `--http --host 0.0.0.0 --port 8000`, path `/mcp`) behind AgentCore Gateway with auth; then set `CLIMATE_RISK_MCP_URL` and add auth headers to `climate_risk_client()` in `weatherwise/agents/orchestrator.py`.
- [ ] **3.4 The 6 AM warning job:** EventBridge Scheduler → Lambda that groups subscribers with `recipient_groups_for_area` (`weatherwise/risk/recipient_groups.py`) and invokes the runtime with `{"type": "warning", "group": ...}`; DynamoDB ledger and SQS outbox replace the in-memory ones in `weatherwise/agents/delivery.py`. Only meaningful with WhatsApp.
- [ ] **3.5 WhatsApp** (AWS End User Messaging Social): only if it passes the Day 4 gate in the plan.
- [ ] **3.6 Amazon Location** for place search and names in production (Nominatim's public service allows 1 request/s).

---

## Things that must stay true (check after every deploy)

- Places outside India say "not covered yet" and show **no Indian helpline numbers** (Kenya check in 1.6).
- Flood shelter answers **never** contain a map route (`directions_link` is null for floods).
- The site states "Not an official warning service. Always follow IMD." and 112 / 108 / 1077 are one tap away.
- No personal data in logs: the API logs no message text or locations; keep CloudWatch retention short.
