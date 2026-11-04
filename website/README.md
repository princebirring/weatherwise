# WeatherWise website

Two parts, one React + Vite + TypeScript app:
- `/app`: the app for farmers and households: pick a place, then **Today** (official warnings
  first, then our own checks for the week), a page for each danger (heat, dry spell, rain and
  flood) with what to do, the nearest checked shelter for heat and floods, and the flood guide, **Ask** (chat with the agents)
  and **Help** (one tap to 112 / 108 / 1077).
- The public site: `/` (landing, with the real app in a phone), `/how-it-works`, `/impact`
  (replays, and this morning's agent run at `/impact#live`), `/developers` (the MCP tools) and
  `/about` (the team).

Every word is in `src/text/{en,hi,mr}.ts`; Hindi and Marathi are full typed copies, so the build
fails if a key is missing. Safety advice is not here: it comes from `rules/languages/*.toml`
through the API.

```bash
npm install
npm run dev     # with the API running: uv run python -m weatherwise.api.server (port 8080)
npm test        # every screen in English, Hindi and Marathi
npm run build   # output in dist/, served by the API or any static host
```
