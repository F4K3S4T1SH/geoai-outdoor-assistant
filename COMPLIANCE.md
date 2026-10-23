# Rulebook compliance and remaining responsibilities

Audit date: 23 October 2026 IST. The rulebook is the authority; this checklist distinguishes implementation and limited verification from guarantees.

| Rulebook item | Evidence / position |
|---|---|
| Self-run open model, at most 3B parameters | Qwen2.5 1.54B, local CPU, official quantization; no hosted large-model calls at runtime. |
| Public Hugging Face model, card and open licence | Actual GGUF weights, tokenizer/configuration, Apache licence and notice published. Quantized `Llama.from_pretrained` loading and generation verified. Optional Transformers loading documented, not executed on this memory-constrained laptop. |
| Free, open live data and disclosed sources | OSM, Photon, Open-Meteo/CAMS and Valhalla. TTL caching disclosed. Source failures remain visible. No paid or private data source is used. |
| Several nearby places across hours | Up to five eligible candidates; full requested activity duration is checked against hourly forecasts. Missing evidence/time-budget exclusions are disclosed. |
| Wind, roads, traffic, industry, water and greenery | All influence comparison or cautions. Traffic is explicitly a road/time proxy; there is no live congestion measurement. Wind alignment is a proxy, not measured pollution. |
| Ten required activities | Implemented. Eighty-six automated checks cover all ten flows and second-hour hazards. Live SLM activity extraction passed ten varied questions; this does not prove every unseen query. |
| Personal details and messy questions | Explicit profile/age rules, relative dates, weekends, time windows, activity aliases, place confirmation and out-of-scope handling. Profiles use heuristic limits, not clinical validation. |
| Practical preparation and avoidance advice | Activity-specific preparation, condition-based cautions, reasons for rejection and evidence are exposed in the browser and JSON. |
| Every factual claim grounded | Forecast values and mapped places come from fetched/cached responses. Model chooses only supplied candidate indices and evidence keys. Static threshold assumptions, inferred venue sport and traffic proxies are labelled. |
| Public API and source/README | Published links in README; API tested through its public HTTPS hostname. Keeping it reachable throughout judging cannot be proven in advance. |
| 4–6 presentation slides | Six-slide PPTX prepared in submission/. It includes architecture, the model, a recorded worked example and limitations. |
| AI coding assistance and attribution | OpenAI Codex disclosed. Exact runtime model/data sources/libraries documented; OSM attribution visible. |
| No hard-coded example answers | Development fixtures/evaluation inputs are outside runtime answers. The recorded worked example is never loaded by the runtime. |

## Still not something we can honestly claim

- Guaranteed uptime across the future judging window: the laptop, internet and current tunnel must stay running.
- Universal successful recommendations or perfect parsing. Real sources may fail; the assistant must decline or ask for details.
- Live traffic congestion or street-level pollution measurements. The interface explicitly identifies estimates and regional forecasts.
- Medical safety certification, verified venue access or complete geospatial coverage.
- Successful final submission: the user must review the presentation, confirm the registered team details and submit through the organizer's Google Form.

The website and evidence package are ready for review. The Google Form entry and judging-window operation remain outstanding, and the limitations above must be disclosed rather than described as solved.
