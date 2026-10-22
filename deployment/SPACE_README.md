---
title: GeoAI Outdoor Assistant
emoji: 🌤️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
license: mit
---

# GeoAI Outdoor Assistant

By F4K3S4T1SH. A self-run Qwen2.5 1.5B assistant comparing outdoor venues and times with live weather, air-quality and OpenStreetMap evidence.

Open `/docs` for the interactive API. POST questions to `/ask`; `/health` reports model readiness.

Deployment candidate: this configuration still needs a real container build and public end-to-end verification. Public map servers have returned capacity errors during local testing. An error is returned when required source data is unavailable.

Runtime model: Qwen/Qwen2.5-1.5B-Instruct, official Q4_K_M GGUF, Apache 2.0. Code licence: MIT. © OpenStreetMap contributors. Weather: Open-Meteo. Air quality: CAMS via Open-Meteo. Geocoding: GeoNames via Open-Meteo. OpenAI Codex was used as a coding assistant; no hosted large model is used at runtime.

Prototype heuristics are not medical guidance. See the source README for limitations and setup.
