# ISS Tracker

Live position, ground track and visibility footprint of the International Space Station on a
world map.

The backend fetches a two-line element set from CelesTrak every couple of hours and propagates
the orbit locally with SGP4. Positions past and future come out of the same element set, so a
full ground track costs no extra upstream traffic — and CelesTrak going down does not take the
app with it.

---

## Quickstart

```bash
docker compose up --build
```

Then open <http://localhost:8080>. API documentation is at <http://localhost:8000/docs>.

### Running the pieces directly

Backend (Python 3.12+):

```bash
cd backend && uv sync && uv run uvicorn iss_tracker.main:app --reload
```

Frontend (Node 20+), in a second terminal:

```bash
cd frontend && npm install && npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so the browser only ever talks to
one origin. Override the target with `VITE_PROXY_TARGET` if the backend is elsewhere.

---

## Configuration

Copy `.env.example` to `.env` and edit as needed; `docker compose` reads it automatically.

| Variable | Default | Purpose |
|---|---|---|
| `TLE_URL` | CelesTrak GP query for catalogue 25544 | Where element sets come from. |
| `TLE_CACHE_TTL_SECONDS` | `7200` | How long a fetched TLE is served before a refresh is attempted. |
| `TLE_HARD_EXPIRY_SECONDS` | `259200` | Age past which a cached TLE is refused outright (72 h). |
| `TLE_STALE_WARNING_SECONDS` | `86400` | Element-set age that starts logging accuracy warnings. |
| `TLE_FETCH_TIMEOUT_SECONDS` | `10` | Timeout for a single upstream fetch. |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | Comma-separated allowed browser origins. |
| `LOG_LEVEL` | `INFO` | Root log level. Logs are JSON on stdout. |
| `BACKEND_PORT` / `FRONTEND_PORT` | `8000` / `8080` | Host ports published by compose. |

Frontend values are inlined by Vite at build time, so they are build arguments rather than
runtime environment:

| Build arg | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Same-origin path nginx proxies to the backend. |
| `VITE_TILE_URL` | OpenStreetMap standard tiles | Tile template. Point at your own server for anything beyond light use. |
| `VITE_TILE_ATTRIBUTION` | OpenStreetMap credit | Attribution shown on the map. Keep it accurate if you change tiles. |

---

## API

Base path `/api/v1`. All timestamps are UTC, serialised with a `Z` suffix.

| Endpoint | Description |
|---|---|
| `GET /health` | `{"status": "ok", "tle_age_seconds": 1842}`. Returns 503 until an element set has loaded. |
| `GET /iss/position` | Latitude, longitude, altitude, velocity, footprint radius and the TLE epoch used. |
| `GET /iss/track` | Ground track. `minutes_behind` (0–180, default 30), `minutes_ahead` (0–360, default 90), `step_seconds` (5–300, default 30). |
| `GET /iss/stream` | Server-sent events emitting the position payload once a second. |

`tle_age_seconds` is time since the element set was **fetched**, not since its epoch — it tops
out at the cache TTL under normal operation.

Track points arrive in chronological order with longitudes in `[-180, 180]`. Handling the
antimeridian is the client's job; see `unwrapLongitudes` in
`frontend/src/utils/coordinates.ts`.

Errors share one shape:

```json
{ "detail": "Upstream TLE source unavailable", "code": "tle_unavailable" }
```

---

## How it holds up

- **Antimeridian.** A track running from +179° to −179° draws straight back across the map if
  the wrap is taken literally. Rather than cutting the line into segments there, the client
  unwraps the longitudes so they run on past 180° (179, 180, 181…) and draws the result once
  per world copy either side. The track stays one unbroken line across the dateline.
- **Upstream outages.** A refresh failure keeps the previous element set in play until it
  passes the 72-hour ceiling. Only then does the API start returning 503.
- **Rate limiting.** Concurrent cache misses collapse into a single upstream fetch through a
  single-flight lock, so CelesTrak sees one request every couple of hours regardless of load.
- **Staleness.** SGP4 drifts noticeably a few days from epoch, so propagating from an old
  element set logs a warning with the epoch age.
- **Velocity** is the magnitude of the geocentric velocity vector (~27,600 km/h), not the speed
  of the subpoint across the ground.

---

## Development

```bash
# Backend
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy          # strict
uv run pytest -q

# Frontend
cd frontend
npm run lint && npm run format:check
npm run typecheck
npm test
```

### Layout

```
backend/src/iss_tracker/
  api/            routes; they validate, call a service, and return
  services/       tle_client (fetch + parse), propagator (SGP4), iss_service (orchestration)
  core/           single-flight TTL cache, domain errors, JSON logging
  models/         Pydantic request/response models

frontend/src/
  api/            typed fetch wrappers, abortable per poll
  hooks/          polling with backoff, ground-track refresh, motion preference
  components/     map, marker, track, footprint, telemetry
  utils/          antimeridian unwrapping, map styling, formatting
```

---

## Attribution

- Orbital element sets from [CelesTrak](https://celestrak.org/), maintained by Dr T.S. Kelso.
  Please respect their [usage guidance](https://celestrak.org/webmaster.php) — this app fetches
  one element set every two hours regardless of traffic.
- Map tiles &copy; [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, under
  the [Open Database License](https://www.openstreetmap.org/copyright). The default tile server
  is subject to the
  [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/); point
  `VITE_TILE_URL` at your own tile source before deploying anything with real traffic.
- Orbit propagation via [Skyfield](https://rhodesmill.org/skyfield/) and the SGP4 model.

## Licence

MIT — see [LICENSE](LICENSE).
