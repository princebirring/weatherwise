# WeatherWise website

Two parts, one React + Vite + TypeScript app:
- `/app`: the app for farmers and households (Start, Today, What to do, Safe place, Help, flood guide, Ask).
- `/`: the showcase for judges and partners (what it does, disaster replays, how it works).

Every word is in `src/text/{en,hi,mr}.ts`; Hindi and Marathi are full typed copies, so the build
fails if a key is missing. Safety advice is not here: it comes from `rules/languages/*.toml`
through the API.

```bash
npm install
npm run dev     # with the API running: uv run python -m weatherwise.api.server (port 8080)
npm test        # every screen in English, Hindi and Marathi
npm run build   # output in dist/, served by the API or any static host
```
