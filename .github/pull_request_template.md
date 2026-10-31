## What and why

<!-- What does this change, and why? Link the issue: "Closes #123". -->

## Which part it serves

<!-- Tick what applies. Every change should serve at least one. -->
- [ ] Part 1: heat-wave and drought early warning for smallholder farmers
- [ ] Part 2: cooling center / shelter router
- [ ] Part 3: flood-risk household guide
- [ ] Platform (tests, deployment, docs)

## How it was tested

<!-- Commands run and what you checked by hand (screens, languages, places). -->

## Checklist

- [ ] `uv run ruff check weatherwise tests scripts evals` and `uv run pytest -m "not live"` pass
- [ ] Website: `npm run lint && npm test && npm run build` pass (if the website changed)
- [ ] New behaviour has tests; a bug fix has a test that failed before the fix
- [ ] No secrets, personal data or real people's locations in code, tests or logs
- [ ] Docs and `CHANGELOG.md` updated if behaviour or setup changed

## Safety (fill in if you touched `rules/`, `skills/`, language files or messages)

- [ ] Every new or changed threshold or safety line cites its source (IMD, NDMA, KVK, ICAR)
- [ ] Translations are checked by a native speaker, or marked `DRAFT` / `CONFIRM`
- [ ] The safety rules in [CONTRIBUTING.md](../CONTRIBUTING.md#safety-rules) still hold
