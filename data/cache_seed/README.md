# Cache seed

Places worked out before deploy, shipped read-only in the image so they load at once after
every deploy: climate baselines (`normals`), river flood levels and river screens (`flood_level`),
place lookups (`admin`) and heights (`elevation`). Same file format and names as the runtime cache
(`weatherwise/cache.py`); entries expire on the same schedule.

A new place's baselines need decades of daily history, about 3,000 of Open-Meteo's 10,000 free
calls a day. To add places, run them locally (e.g. `uv run python -m evals.eval_replays`, or open
them in the app), then copy those four folders from `cache/store/` here.
