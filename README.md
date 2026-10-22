# GeoAI Outdoor Assistant

Project owner: `F4K3S4T1SH` on GitHub and Hugging Face.

- Source: https://github.com/F4K3S4T1SH/geoai-outdoor-assistant
- Public model configuration: https://huggingface.co/F4K3S4T1SH/geoai-outdoor-model
- Public judging API: not deployed yet.

Working prototype for GeoAI Hackathon 2026. Parses free-form questions with a locally run Qwen2.5 1.5B model, finds named OpenStreetMap venues, and ranks place/hour combinations using live forecast data and explicit geographic heuristics.

## Run on this Windows laptop

The local Python environment, CPU runtime and model are set up by the development session. Run `./start.ps1` from PowerShell, then open http://127.0.0.1:8000/docs. The `/health` endpoint reports whether the model has loaded. Both services listen on the local machine only. Do not start the script a second time while the first instance is running.

POST `/ask`:

```json
{"question":"Where can I go running tomorrow morning near Powai?","latitude":19.1176,"longitude":72.9060}
```

Coordinates are optional but recommended for neighbourhoods. The city geocoder may not resolve neighbourhood names; ambiguous matches return a clarification rather than guessing. Current date is resolved in Asia/Kolkata. Supply a time range within five days. `/activities` lists the ten supported activity categories.

To recreate Python dependencies: Python 3.12+, `python -m venv .venv`, then `.venv/Scripts/python.exe -m pip install -r requirements.txt`. Development checks also require pytest.

Runtime: official llama.cpp Windows CPU x64 release b11823, downloaded from https://github.com/ggml-org/llama.cpp/releases/tag/b11823 into `runtime/llama`. Model: official `Qwen/Qwen2.5-1.5B-Instruct-GGUF`, `qwen2.5-1.5b-instruct-q4_k_m.gguf` in `models/`. Base model: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct (1.54B parameters, Apache 2.0). No fine-tuning. Model inference stays on localhost. No large hosted model is used by the running application.

## Data and attribution

- OpenStreetMap through Overpass API: venues, roads, industry, water and green features. © OpenStreetMap contributors. https://www.openstreetmap.org/copyright
- Open-Meteo forecast API: hourly weather and daylight. https://open-meteo.com/en/docs
- CAMS through Open-Meteo air quality API: regional forecast US AQI, not a local sensor reading. https://open-meteo.com/en/docs/air-quality-api
- GeoNames through Open-Meteo geocoding API. https://open-meteo.com/en/docs/geocoding-api

Responses expose request parameters, fetch timestamps, cached status and actual values. Weather/AQI cache TTL is 15 minutes, map queries one hour, geocoding one day. Calls are serialized and spatial queries are bounded. Source outages are reported; no canned weather or venue data is substituted. Data remains subject to source licences and service limits; this prototype is for noncommercial hackathon use.

## Architecture

Question → local SLM JSON extraction → validated place/time/profile → geocode → Overpass compatible venues → per-venue hourly weather/AQI and map context → deterministic eligibility checks and ranking → structured evidence, alternatives and precautions.

The model extracts intent, then compares a shortlist of eligible candidates and cites evidence keys. Code verifies its choice and renders actual values. Explicit relative dates and profile keywords are checked separately after extraction because CPU model testing exposed errors in both. Geography and weather calculations are explicit code. Heuristic thresholds are development assumptions, not medical guidance or scientifically validated safety limits.

## Known limitations and work remaining

- Not deployed; no public judging endpoint yet.
- Public team model configuration repository and model card are published. The original unchanged base model loads with upstream `from_pretrained`; the CPU runtime uses its official GGUF artifact.
- Presentation and live demo package still need preparation.
- No live traffic, route estimation, full activity duration checks or verified venue hours.
- Candidate search compares at most five nearest compatible named mapped venues. OSM sport tagging and access coverage vary; cycling venues do not imply verified cycling routes.
- Wind alignment is a crude proxy only; nearest mapped geometry vertices are used, not full line/polygon distances or a dispersion model.
- Health profiles tighten heuristic limits. No guarantee of medical safety.
- Response currently provides structured evidence and generic preparation advice rather than polished narrative.
- Tests must be supplemented with varied live and adversarial model queries before submission.

## Verified development status — 23 October 2026 IST

- Official GGUF downloaded and SHA256 verified against Hugging Face metadata.
- Local CPU inference operational; initial extraction requests took approximately 3.5–4.7 seconds. An extraction plus candidate comparison took 6.95 seconds in a synthetic-candidate check.
- Fifteen automated tests pass, including source failure, wind orientation, profile limits, relative dates and a fixture-based recommendation flow.
- Live weather, air quality and geocoding calls succeeded, although a later weather request timed out. Map requests initially failed but a later venue query succeeded.
- A complete live development flow compared 20 place/hour combinations across five venues near Powai. It returned `avoid_or_insufficient_data`: forecast US AQI 161 exceeded the general-profile prototype limit; the earliest hour also failed the daylight check. One venue had unavailable data. Total latency was 201.59 seconds. This validates an evidence-based rejection, not a positive recommendation. The recorded result is in `submission/live-example.json` and is never used as a runtime fallback.
- Local API and model health verified. Source and model configuration repositories are published. Public hosting remains pending.

## Disclosure

Built with OpenAI Codex as an AI coding assistant, with human direction and review. Runtime language model: Qwen2.5-1.5B-Instruct only. Open-source libraries: FastAPI, Uvicorn, HTTPX, Pydantic, tzdata, llama.cpp. Hugging Face Hub is used to download public weights; pytest is used in development.

## Deployment preparation

`Dockerfile` builds the pinned llama.cpp CPU server and serves FastAPI on port 7860. `deployment/serve.py` downloads pinned official weights, verifies SHA256, waits for local model readiness and supervises both processes. The image has not yet been built or tested; Docker is not installed on this development laptop.

Hugging Face's current Spaces overview says Docker Spaces require a paid plan: https://huggingface.co/docs/hub/spaces-overview. No plan or hardware upgrade has been purchased. `deployment/publish_space.py` defaults to a dry run and requires `--publish` to upload. A laptop with a public tunnel is another hosting option, but it requires keeping the laptop awake and connected and verifying the endpoint throughout judging.

Use browser/device authorization via `runtime/gh/bin/gh.exe auth login --web` and `.venv/Scripts/hf.exe auth login`. Never place tokens in the repository or chat. `deployment/publish_model.py` uploads only the reviewed model card and configuration after verifying the signed-in username.
