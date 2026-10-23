# Outside — GeoAI outdoor planner

A browser frontend and HTTP API that compare outdoor places and times using a locally run Qwen2.5 1.5B model, live weather, air quality and OpenStreetMap evidence. Built for GeoAI Hackathon 2026 by **F4K3S4T1SH**.

- Website: https://heavily-investment-chose-computer.trycloudflare.com/
- Judging API: **POST** https://heavily-investment-chose-computer.trycloudflare.com/ask
- API schema / tester: https://heavily-investment-chose-computer.trycloudflare.com/docs
- Model and actual GGUF weights: https://huggingface.co/F4K3S4T1SH/geoai-outdoor-model
- Source: https://github.com/F4K3S4T1SH/geoai-outdoor-assistant

The public address is temporary: the laptop and tunnel must remain running. A tunnel restart changes the hostname. See [HOSTING.md](HOSTING.md).

## Use the website

Write a question, optionally choose an activity or profile, and confirm your neighbourhood from live place-search results. You can specify dates, duration, radius and a cycling commute destination. Dates use **Asia/Kolkata (IST)**. The result shows the chosen window, alternatives or reasons for declining, a map, preparation advice and timestamped source evidence. Unknown or ambiguous places are confirmed rather than silently guessed.

## Run locally

Python 3.12+ is required. Create a virtual environment and install `requirements.txt`; add pytest for development. This laptop already has those dependencies.

Runtime binaries and weights are intentionally excluded from Git:

- Official llama.cpp **b11823**, Windows CPU x64 release: https://github.com/ggml-org/llama.cpp/releases/tag/b11823 . Extract into `runtime/llama/`.
- `Qwen/Qwen2.5-1.5B-Instruct-GGUF`, revision `91cad51170dc346986eccefdc2dd33a9da36ead9`, file `qwen2.5-1.5b-instruct-q4_k_m.gguf`, in `models/`.
- SHA256: `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.

Run `./start.ps1`, then open http://127.0.0.1:8000/ . For public laptop hosting use `./start-public.ps1`; to stop public access use `./stop-public.ps1`. The model listens only on localhost port 8081; the public connection forwards the application on port 8000.

## API example

```json
{"question":"Where can I run tomorrow morning within 5 km of Powai?","latitude":19.1176,"longitude":72.906}
```

Optional confirmed fields: `activity`, `profile`, `location`, `radius_km`, `start`, `end`, `duration_minutes`, `mode`, `destination`, `destination_latitude`, `destination_longitude`, `max_travel_minutes`. Full schema is at `/docs`. Coordinates are optional. Search dates must be within the next five days. Missing details return a clarification; unsupported questions return an out-of-scope response. `/locations?q=...` searches places, `/activities` lists categories, and `/health` reports readiness.

One question is processed at a time. Concurrent requests receive HTTP 429 / Retry-After. The overall budget is 85 seconds, with shorter evidence budgets per venue. A timeout never triggers canned weather or place answers.

## Architecture and reasoning

Question → self-run SLM extracts intent → explicit dates, duration, profiles and confirmations are checked → live mapped candidates → hourly weather/AQI plus geographic context → full-duration suitability checks → SLM compares eligible candidates → verified evidence references and browser results.

Ten activity categories are implemented: running, cycling, golf, cricket, football, tennis, hiking/walking, picnic, event and photography. Cycling commutes require a confirmed destination and a verified bicycle route. Leisure cycling candidates require a route too. Travel times are road-network estimates, not live congestion estimates. Sunset requests use forecast sunset times, with a disclosed low-light photography window.

Mapped road proximity, wind direction and weekday commute hours form a **traffic/exposure proxy**. Nearby water contributes edge/footing cautions and penalties; mapped greenery contributes a small preference bonus. These are transparent prototype rules, not pollution dispersion, flood, shade or medical models. Profiles and explicit ages tighten heuristic limits. Exact rules are in `geoai/ranking.py`; advice varies by activity and observed conditions.

## Data, attribution and service use

- **© OpenStreetMap contributors** — venues and geography via Overpass; limited place-search fallback via Photon. https://www.openstreetmap.org/copyright
- Photon / komoot — neighbourhood lookup and a bounded OSM venue fallback. https://github.com/komoot/photon
- Open-Meteo — hourly forecast and sunrise/sunset. https://open-meteo.com/en/docs
- CAMS via Open-Meteo — regional **US AQI** forecasts, not street-level sensor readings. https://open-meteo.com/en/docs/air-quality-api
- GeoNames via Open-Meteo — geocoding fallback. https://open-meteo.com/en/docs/geocoding-api
- Valhalla / FOSSGIS — live route requests using open OSM road data. https://valhalla.github.io/valhalla/api/
- Browser map: Leaflet 1.9.4 and standard OSM tiles, with visible attribution. No bulk/offline tile downloading. https://operations.osmfoundation.org/policies/tiles/

Weather/AQI cache TTL is 15 minutes; static Overpass map data and geocoding are cached up to 24 hours; routes and Photon venue searches one hour. Source calls are serialized per service, spatial queries are bounded, rate spacing and cooldowns are applied, and timestamps/cache status are returned. Missing geographic context prevents a positive recommendation, but available forecast evidence and the missing checks are shown. A sport inferred from a mapped venue name in the fallback is explicitly labelled and must be confirmed with the venue.

## Verified checks and limitations

- **86 automated checks pass**, including all ten activity flows, two-hour windows with a thunderstorm in the second hour, geographic scoring, profiles, date normalization, missing data and timeouts. These use synthetic fixtures and do not prove coverage of every real venue.
- A live local model evaluation classified **10/10** varied activity requests after normalization. See `submission/model-evaluation.json`; this small test set is not a general accuracy claim.
- Public model LFS SHA256 verified. `llama_cpp.Llama.from_pretrained` loaded the submitted repository snapshot and generated `OK`; see `submission/model-loading-check.json`. The optional Transformers GGUF path is documented but was not run because full dequantization exceeded free memory.
- Real venue, weather, AQI, geocoding and bicycle-route calls have succeeded. Public map APIs have also repeatedly timed out. The application reports missing evidence, not a fabricated recommendation.
- The recorded Powai worked example rejected unsuitable options. `submission/live-example.json` is evidence of a historical run, never a runtime fallback. One public warm-cache request took 16.56 seconds; that is not a latency guarantee.
- No live congestion feed, street-level AQI, verified venue hours, booking availability or ground inspection. Commutes sample weather/context near the route midpoint, not every metre. At most five compatible venues are assessed; time budgets may reduce that number, with omissions disclosed.
- Laptop hosting has no uptime guarantee. Final submission and keeping the endpoint online through judging remain human responsibilities. See [COMPLIANCE.md](COMPLIANCE.md).

## Model, licences and development disclosure

Base model: **Qwen/Qwen2.5-1.5B-Instruct**, 1.54B parameters, open weights under Apache 2.0. No fine-tuning. Official Q4_K_M weights are redistributed unchanged in the public model repository with licence and attribution. The small model runs on the laptop; no large hosted model runs inside the assistant. The model card includes tested quantized `from_pretrained` instructions.

OpenAI Codex helped write and test the code. Libraries/tools: FastAPI, Uvicorn, Pydantic, HTTPX, tzdata, llama.cpp, Hugging Face Hub, Leaflet, Cloudflare Tunnel and pytest. Optional loading checks use llama-cpp-python; the separate verification environment also installed PyTorch/Transformers. Frontend fonts: DM Sans and Manrope from Google Fonts. Application code is MIT; model and data licences remain separate.

The six-slide presentation is `submission/outside-geoai-hackathon.pptx`. Docker hosting files are an optional, unverified deployment candidate, not the active hosting route. No paid plan has been purchased.

### Map outage handling

Fresh map cache entries remain usable during provider cooldowns. If Overpass fails, the app retrieves a small read-only OSM map extract around each venue (and one search-centre extract when venue search fails), serialized and cached for 24 hours. These extracts can omit unmapped features and enclosing polygons. This is a bounded prototype fallback, not a bulk downloader. Conditions that fail the prototype thresholds and incomplete evidence have separate result labels; missing checks prevent a positive recommendation. Comparison counts distinguish weather availability from complete checks.

OSM map API reference: https://wiki.openstreetmap.org/wiki/API_v0.6#Retrieving_map_data_by_bounding_box:_GET_/api/0.6/map

### Exercise distance and exact venues (v0.3.0)

�10 km run in Bharathi Park� means a 10 km exercise target at that venue, not a nearby search. A confirmed OSM identity is verified from map data and held fixed. If it cannot be verified, no other park is substituted. The app compares time windows at that venue; �near Bharathi Park� continues to compare nearby places.

Use `exercise_distance_km`, `pace_minutes_per_km` or `duration_minutes`, `venue_scope` (`exact` or `nearby`) and a confirmed `venue_id` from `/locations`. When a distance target has neither an explicit duration nor pace, the API requests clarification instead of assuming one hour. Duration from pace is rounded up to whole minutes. An exact venue response has `radius_km: null` and `search_radius_applied_km: null`.

Travel directions carry `purpose: travel_to_venue` and are not exercise routes or exercise-duration estimates. Exact-venue requests do not invent an origin-to-park journey. **This application assesses conditions, not a measured running course**: exercise targets include `exercise_route.status: not_verified`; no park lap length, 10 km course or repetition count is invented. Positive distance-based results are labelled condition windows with the course unverified. See `submission/exact-venue-live-example.json` for a real public API recording.
