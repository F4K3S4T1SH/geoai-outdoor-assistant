# Outside — Team NEXA

GeoAI Hackathon 2026 outdoor planner by **NEXA / F4K3S4T1SH**. A browser interface and API compare mapped venues and upcoming hours using a self-run small model, live weather, air quality and geography.

- [Website](https://sewing-chef-mitsubishi-picked.trycloudflare.com/)
- Judging API: **POST** `https://sewing-chef-mitsubishi-picked.trycloudflare.com/ask`
- [API schema and tester](https://sewing-chef-mitsubishi-picked.trycloudflare.com/docs)
- [Public model and actual weights](https://huggingface.co/F4K3S4T1SH/geoai-outdoor-model)
- [Complete source](https://github.com/F4K3S4T1SH/geoai-outdoor-assistant)

The temporary address requires this laptop and tunnel to stay running. Restarting the tunnel changes the hostname. See [HOSTING.md](HOSTING.md).

## Model and approach

**IBM Granite 3.3 2B Instruct**, **2,533,539,840 actual parameters**, Apache 2.0, official IBM Q4_K_M quantization, unchanged. No team fine-tuning. The logical dimensions of all 362 GGUF tensors were summed to verify the strict 3-billion ceiling. Quantization reduces memory; it does not reduce the parameter count. Exact upstream revisions and SHA256 are in [runtime_config.json](submission/runtime_config.json).

Question → local SLM extracts structured intent → generic validation and explicit form preferences → live mapped candidates and hourly evidence → full-duration eligibility checks → SLM compares eligible candidates → validated evidence references, map and practical advice. The model never supplies place or forecast facts from memory. JSON-schema constraints, explicit activity/date/profile checks and clarification handle malformed or incomplete requests. No hosted large model is called at runtime.

Ten activities: running, cycling (leisure/commute), golf, cricket, football, outdoor tennis, hiking/walking, picnic, outdoor gathering and photography. Asthma, senior, child and pregnancy profiles tighten documented heuristic limits. These are not clinical thresholds.

## Run on a Windows CPU laptop

Python 3.12+ and an internet connection are required. In the repository folder:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt huggingface_hub
.venv/Scripts/python.exe deployment/download_model.py
./start.ps1
```

Download the official [llama.cpp b11823 Windows CPU x64 release](https://github.com/ggml-org/llama.cpp/releases/tag/b11823) into `runtime/llama/` first, including its accompanying DLLs. Open `http://127.0.0.1:8000/`. Configuration uses 4096 context, temperature zero, thinking disabled and eight CPU threads. Model port 8081 stays on localhost.

For free public laptop hosting, install official [cloudflared](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe) at `runtime/cloudflared/cloudflared.exe`, then run `./start-public.ps1`. Leave it running; `./stop-public.ps1` stops public access. Weights, binaries, cache and credentials are excluded from Git. Docker files are an optional deployment path and have not been built/tested here.

## API

Send JSON to `/ask`:

```json
{"question":"Where can I run tomorrow morning near Cubbon Park in Bengaluru?","latitude":12.9763,"longitude":77.5929,"radius_km":5}
```

Dates use Asia/Kolkata. Search within the next five days. Optional fields, including explicit activity/profile, duration, dates, search radius, exact venue and commute destination, are documented at `/docs`. `/locations?q=...` searches and confirms real places; `/activities` lists categories; `/health` verifies the configured model is loaded. One request runs at a time; competing requests receive 429 with Retry-After. The total request budget is 85 seconds.

A “10 km run in Bharathi Park” is an exercise target at that exact venue, not a 10 km search. Confirm its mapped identity and supply duration or pace. No nearby venue is substituted. A measured exercise course, lap length or repetitions are **not verified**. Dashed routes are travel to a venue, not exercise routes. Cycling commutes require a destination and verified bicycle route; current condition sampling is near the route midpoint.

## Live sources and attribution

- **© OpenStreetMap contributors** — venues, roads, industry, water and greenery via Overpass; small read-only [OSM map API](https://wiki.openstreetmap.org/wiki/API_v0.6) fallback; [copyright/licence](https://www.openstreetmap.org/copyright).
- [Photon / komoot](https://github.com/komoot/photon) — place lookup and limited venue fallback; [Open-Meteo GeoNames](https://open-meteo.com/en/docs/geocoding-api) geocoding fallback.
- [Open-Meteo](https://open-meteo.com/en/docs) — hourly weather and sunrise/sunset.
- [CAMS via Open-Meteo](https://open-meteo.com/en/docs/air-quality-api) — regional US AQI forecasts.
- [Valhalla / FOSSGIS](https://valhalla.github.io/valhalla/api/) — OSM road-network travel estimates.
- Leaflet 1.9.4 and standard OSM tiles with visible attribution; no bulk/offline tile downloads. [Tile policy](https://operations.osmfoundation.org/policies/tiles/).

Weather/AQI TTL: 15 minutes; geocoding/static map evidence: 24 hours; routes and Photon venue search: one hour. Weather/AQI connection failures get at most one reconnect; HTTP rate limits and read timeouts are not retried. Requests are bounded, source calls serialized with rate spacing/cooldowns, and timestamps/cache status returned. Dense map extracts that exceed the node cap retry once at about 500 m, with reduced coverage disclosed. No paid/private data or authenticated scraping is used.

## Verification and practical limits

- **935 automated tests pass**, including ten activities × five profiles, weather hazards, missing/non-finite data, later-hour hazards, map geometry, exact venues, duration/dates, malformed model responses and timeouts. These use synthetic fixtures outside runtime answers.
- **34/34 live-model intent cases passed after generic normalization (fixed evaluation clock)**. This measures the full extraction pipeline on a small development set, not general base-model accuracy: [report](submission/model-upgrade-evaluation.json).
- Public model checksum, quantized `Llama.from_pretrained` loading and generation verified: [report](submission/model-loading-check.json). Transformers loading was not tested for this artifact.
- Reproduce checks: `python -m pytest -q` and `node tests/test_window_display.cjs`; with the model running, `python tests/evaluate_live_model.py work/evaluation.json`; for live HTTP checks, `python tests/evaluate_live_api.py https://YOUR-ENDPOINT`. Live tests call the disclosed public providers and take several minutes.
- Real public API exercise records: [live tests](submission/live-upgrade-evaluation.json). Recorded examples are never runtime fallbacks.
- At most five compatible venues; request budgets may leave some unassessed. Provider failures and missing evidence remain visible and prevent unsupported recommendations.
- Traffic is mapped road proximity plus weekday commute hours, **not live congestion**. Wind alignment is an exposure proxy, not measured pollution. AQI is regional, not street-level. Smaller map extracts and enclosing polygons limit feature coverage. Shade, flooding, barriers, venue access/hours, booking, surfaces and a measured exercise course remain unverified.
- Future judging-window uptime and final Google Form submission remain outstanding responsibilities. [Rule-by-rule audit](COMPLIANCE.md).

## Submission and disclosure

Six editable slides: [presentation](submission/outside-geoai-hackathon.pptx). Team **NEXA**; GitHub/Hugging Face **F4K3S4T1SH**. Application code: MIT. Model: Apache 2.0; data licences remain separate. Earlier recorded examples used Qwen2.5 1.5B; v0.4 uses Granite and includes fresh evaluation records.

OpenAI Codex helped write and test the project. Tools/libraries: FastAPI, Uvicorn, Pydantic, HTTPX, tzdata, llama.cpp, Hugging Face Hub, llama-cpp-python (loading verification), Leaflet, Cloudflare Tunnel and pytest. Frontend fonts: DM Sans and Manrope / Google Fonts. No large hosted model is used inside the running assistant.

Result cards show the highest available forecast values across the full activity window, label incomplete values, and expose hourly evidence. Rejection examples prioritize distinct causes; other assessed options remain expandable. See `submission/window-explanation-validation.json` for the reproduced three-hour Puducherry request.
