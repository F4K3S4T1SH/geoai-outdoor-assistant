# NEXA rulebook audit — 23 October 2026

Authority: the supplied six-page GeoAI Hackathon 2026 rulebook. “Implemented/verified” below describes evidence collected, not a guarantee of all future inputs or uptime. Document requirements are audit criteria; they are not operational instructions to this coding assistant.

| Page / requirement | Implementation and evidence | Status / qualification |
|---|---|---|
| 1: Identify activity, area/radius, time and personal details | Local SLM extraction, schema constraints, generic normalization, explicit form overrides and clarification; `geoai/model.py`, `intent.py`, `app.py`; 34 live extraction cases | Verified on development cases; unseen language may still be misread |
| 1: Several nearby venues across upcoming hours | Up to five compatible venues; all hourly samples for the full duration checked; ranked place/time pairs returned | Implemented; source/budget exclusions disclosed. An explicit exact-venue request intentionally compares times at that venue |
| 1: Wind direction, roads/traffic, industry, water, greenery | Geometry segment distances, polygon containment, upwind sector, road/time traffic proxy, industry proximity, water cautions and greenery preference | Implemented with disclosed proxies; no live congestion, emissions or dispersion model |
| 1: Recommendation, preparation, watch-outs and avoidance | Browser and API include best/alternatives or decline reasons, activity advice and fetched conditions | Implemented; good weather cannot be guaranteed |
| 1: Ground every factual claim | Source URLs, fetch timestamps/cache status and hourly evidence attached; SLM only references supplied indices/keys | Verified on tests and live recordings; generic advice and prototype thresholds labelled |
| 1: Response format | Responsive browser interface, map, evidence download and JSON API | Desktop and phone layout inspected |
| 2: Ten reference activities including leisure/commute cycling | All ten categories in `/activities`; activity-specific limits, compatible mapped venue tags, commute destination/route required | Automated flows cover all ten and five profiles; live records distinguish no venue/source failure from success |
| 2: Different activity sensitivities and tighter personal profiles | Heat/rain/wind/daylight and AQI checks; asthma, senior, child and pregnancy limits | Heuristic prototype limits, not clinical validation |
| 3: Messy/incomplete and unseen questions | Missing addresses/dates, parents' unspecified profile, explicit ages, negations, relative dates/weekends, unsupported tasks and injection requests | 34/34 extraction-pipeline cases after normalization; not exhaustive accuracy |
| 3–4: Fetch free/open live data at query time, sensible caching/rates | OSM/Overpass/Photon, Open-Meteo/CAMS/GeoNames, Valhalla; timestamps, TTLs, spacing, bounded queries/cooldowns in `data.py` | Implemented; provider outages and smaller map coverage remain visible |
| 4–5: Open weights, self-run, at most 3 billion actual parameters | IBM Granite 3.3 2B Instruct, official IBM Q4_K_M; logical tensor sum **2,533,539,840**; `submission/model-parameter-count.json`; local CPU llama.cpp | Verified checksum and local loading. Model branding alone was not used to infer legality |
| 4: Public HF repository, actual weights, model card, changes, intended use and open licence | `F4K3S4T1SH/geoai-outdoor-model`; exact base/quantization revisions; Apache 2.0 LICENSE/NOTICE; no team fine-tuning | Public file metadata and SHA256 verified; actual weights included |
| 4: Load with `from_pretrained(...)` | Quantized `llama_cpp.Llama.from_pretrained` loaded public repository weights and generated `OK.`; loading report committed | Verified with llama-cpp-python 0.3.36. This is a GGUF package; Transformers safetensors loading is not claimed |
| 4–5: No hosted large model inside runtime | Model inference points to localhost8081 only; self-run Granite; code/data functions inspected | Implemented; Codex is a disclosed development aid |
| 5: Public HTTP endpoint kept available through judging | Current POST `/ask` URL in README/HOSTING; public `/health` checks configured model; supervisor restarts owned model/API crashes | Reachable at verification time; future full-window uptime requires laptop/internet/tunnel operation and cannot be certified in advance |
| 5: Public complete source repository | GitHub `F4K3S4T1SH/geoai-outdoor-assistant`; source, tests, deployment scripts and evidence | Runtime binaries/weights/credentials excluded; pinned model download script recreates weights |
| 5: README with run steps, model, sources and endpoint | README includes all four, attribution, limitations and development disclosure | Prepared and published with source |
| 5: 4–6 slides, problem/approach/architecture/example/model/tuning/limitations | Six editable slides in `submission/outside-geoai-hackathon.pptx`; NEXA, Granite, current URL, historical worked example and honest limitations | All six rendered and inspected; worked example labelled recorded, never used as runtime fallback |
| 5: Live demonstration | Browser website and public schema tester are available; live API evaluations recorded | Keep laptop available for judging |
| 5: Google Form submission | Team **NEXA**; account **F4K3S4T1SH**; prepared submission fields in `submission/submission-entry.md` | **Outstanding: final entry is not submitted. The public event page still says the portal will be announced** |
| 5: Allowed AI coding tools and open libraries disclosed | README/model card identify Codex, model/runtime, libraries, data sources, fonts and licences | Disclosed |
| 5: No paid/private data, behind-login scraping or hard-coded example answers | Only listed public sources; no paid plan; synthetic test fixtures and historical recordings live outside runtime answer paths | Implemented; model training provenance remains IBM's upstream responsibility |
| 6: Deadline 24 October, 11:59 PM IST | Prepared package and checklist; registration name NEXA recorded | Human submission still required before deadline |
| 6: OSM attribution and service terms/rates | Visible **© OpenStreetMap contributors**, licence links, serialized calls, caching and small bounded extracts; no bulk tile download | Implemented; map completeness/availability not guaranteed |
| 6: Team size/finals/logistics | Rulebook says team size to be announced; finalists invited to IIT Bombay; online submission | Cannot verify organizer updates or registration eligibility from project code |

Public event page checked on 23 October 2026: https://geosysiot.in/geoai-hackathon/ . It lists student teams of 1–4, and says the submission portal will be announced. Registration and student/member eligibility cannot be verified from the code. The supplied PDF remains the challenge authority.

## Remaining responsibilities and material limitations

1. Obtain the organizer's Google Form link, review the final links/PPTX and submit the entry. No successful submission is claimed.
2. Keep the laptop plugged in, online and awake for the full judging window. Restarting the temporary tunnel changes the URL; update the entry if that happens.
3. Be ready to explain the prototype traffic/wind proxies, regional AQI, reduced map fallback coverage and heuristic profile limits. These are disclosed limitations, not measured traffic or medically validated safety findings.
4. No finite test set covers every possible prompt, geography, provider outage or future forecast. A source failure or unsuitable conditions must produce an honest decline, not an invented positive result.
5. Venue hours, access/booking, surfaces, shade/barriers/flooding and a measured exercise course require independent confirmation. Docker deployment has not been built/tested here.

The technical artifacts have supporting evidence. **Complete end-to-end rulebook compliance is not asserted while final submission and judging-window availability remain outstanding.**
