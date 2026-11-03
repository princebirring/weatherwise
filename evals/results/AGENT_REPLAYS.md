# Past disasters, replayed through the agent

Model: `us.amazon.nova-micro-v1:0` on Amazon Bedrock. Run 2026-11-02 with `uv run python -m evals.eval_agent_replays`.
Each morning gets only the forecasts issued then. Plain code decides whether to warn; the agent
writes the message; the Evaluator checks it and sends unsafe drafts back; delivery rules decide
what one household would have received (normal warnings 7 AM-8 PM, at most 3 per event, 4 a month).
Every message is in `evals/results/agent_replays/<event>.json`.

| Event | Language | First warning | Mornings flagged by code / with a checked message | Messages a household got | Drafts the Evaluator sent back | Safe fallbacks | Model calls | Slowest morning | Model cost |
|---|---|---|---|---|---|---|---|---|---|
| Kolhapur-Sangli floods, July 2024 | mr | 9 days before | 11 / 11 | 4 | 14 | 1 | 46 | 6.75 s | $0.00264 |

Prices: `data/bedrock_prices.toml` (AWS Price List API). Weather data by Open-Meteo.com (CC BY 4.0)
