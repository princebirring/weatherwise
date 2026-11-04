# Contributing to WeatherWise

Thank you for helping. WeatherWise sends heat, drought and flood warnings to people who may act
on them, so a few rules here are stricter than in most projects. Please read the
[safety rules](#safety-rules) before changing anything under `rules/`, `skills/` or the
language files.

By taking part you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

You need [uv](https://docs.astral.sh/uv/) (it installs Python 3.13) and Node.js 22 or newer.

```bash
uv sync                                    # Python dependencies
(cd website && npm ci)                     # website dependencies
uv run pytest -m "not live"                # server tests, offline
(cd website && npm test)                   # website tests, every screen in en / hi / mr
uv run python -m weatherwise.api.server    # API + built website on http://127.0.0.1:8080
```

For website work, run the API and `cd website && npm run dev`. The agents (chat) need a model on
Amazon Bedrock (production uses Amazon Nova Pro): see "Run it" in the [README](README.md).

## Workflow

1. **Open or pick an issue** first for anything bigger than a typo, so the approach can be agreed.
2. **Branch from `main`** with a short, descriptive name:
   `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `refactor/<topic>`, `test/<topic>`, `chore/<topic>`, `ci/<topic>`.
3. **Commit** with [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   <type>(<scope>): <what changed, imperative, lower case>

   <why, wrapped at 72 characters>
   ```
   Types: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `chore`.
   Scopes we use: `risk`, `places`, `weather`, `backtest`, `mcp`, `agents`, `api`, `website`,
   `rules`, `i18n`, `deploy`. Keep each commit to one logical change.
4. **Open a pull request** into `main` and fill in the template. CI must pass and one maintainer
   must approve. Maintainers squash-merge or merge with a merge commit; please do not force-push
   after review has started.

## Before you open a pull request

- [ ] `uv run ruff check weatherwise tests scripts evals` is clean.
- [ ] `uv run pytest -m "not live"` passes; run `uv run pytest -m live` too if you touched weather, places or the MCP server.
- [ ] `cd website && npm run lint && npm test && npm run build` passes if you touched the website.
- [ ] New behaviour has tests. A bug fix has a test that failed before the fix.
- [ ] Docs updated (`README.md`, `infra/ARCHITECTURE.md`, `CHANGELOG.md`) when behaviour or setup changes.
- [ ] No secrets, personal data, phone numbers or real people's locations in code, tests or logs.

## Code conventions

- **Python:** 3.13, formatted and linted by ruff (settings in `pyproject.toml`). Plain functions
  and dataclasses; the risk engine has no AI and no network calls, so it stays testable offline.
- **Location-agnostic:** never write a place, state, season or time zone into code. They belong in
  `rules/` (global, countries, languages) or `data/`. Pilot towns appear only as test fixtures.
- **One door to facts:** agents and the website get every fact through the Climate Risk MCP
  server (`weatherwise/mcp_server`). Do not read `rules/` or call weather APIs from agent code.
- **Website:** React + TypeScript. Every word lives in `website/src/text/{en,hi,mr}.ts`. Hindi and
  Marathi are full typed copies, so a missing key fails the build. Never write user-facing text
  directly in a component.
- **Names:** say what a thing is (`hazard_outlook`, `keep_guide_on`), not how it works.

## Safety rules

These protect people who may act on a warning. A pull request that breaks one will not be merged.

1. **Numbers come from data, never from the AI.** Messages are checked in code
   (`weatherwise/agents/message_rules.py`); do not weaken a check to make a test pass.
2. **Official warnings always win.** They show first, before our own checks, and must still show
   when our forecast is down. If they cannot be checked, say so: never show that as "no warnings".
   Thresholds from an official service (IMD) go in `rules/countries/<code>.toml` with the source in a
   comment. Our own rules are labelled "ours".
3. **"Move now" only on an official red alert or extremely heavy rain within a day.** Our model
   data alone only ever starts the flood guide in prepare mode.
4. **"High ground" never without "away from hill slopes"** (landslides), and **no map routes in
   floods**. Tests enforce both, in every language.
5. **Safety text and its translations** (`rules/languages/*.toml`, `skills/`) must cite a source
   (NDMA, IMD, KVK, ICAR) and be checked by a native speaker. Mark unverified text `TODO` (falls back
   to English) or `DRAFT` / `CONFIRM` in a comment, and say so in the pull request.
6. **Places we do not cover** must say so honestly and show no helpline numbers from another country.
7. **Switch a rule off in `rules/`, never by deleting its code** (`[checks] enabled`,
   `[flood_guide] prepare_signals`, `[forecast_correction] enabled`). Before changing a threshold or
   a switch, replay the headline events (`uv run python scripts/backtest.py --headline`) and put the
   before and after scores in the pull request.

## Reporting bugs and ideas

Use the issue templates. For a wrong or unsafe warning, use the **Safety or translation problem**
template and include the place, date and what was shown. For security problems, see
[SECURITY.md](SECURITY.md); do not open a public issue.

## Licence

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
