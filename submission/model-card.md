---
license: apache-2.0
base_model: Qwen/Qwen2.5-1.5B-Instruct
language:
  - en
tags:
  - geoai
  - outdoor-planning
  - small-language-model
---
# GeoAI Outdoor Assistant — model configuration

This project uses Qwen/Qwen2.5-1.5B-Instruct unchanged (1.54B parameters). No fine-tuning was performed. CPU development inference uses the official Qwen Q4_K_M GGUF through llama.cpp.

## Exact runtime artifact

- Repository: Qwen/Qwen2.5-1.5B-Instruct-GGUF
- Revision: 91cad51170dc346986eccefdc2dd33a9da36ead9
- File: qwen2.5-1.5b-instruct-q4_k_m.gguf
- SHA256: 6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e
- Original model: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct
- Licence: Apache 2.0, retaining upstream notices.

## Use

The model first extracts activity, location, dates, radius and profile as JSON. After live data collection and eligibility checks, it compares only supplied candidates and returns an index and evidence keys. Code validates those references and renders actual forecast values. The model does not supply weather or place facts from memory.

The original base model is loadable with `AutoTokenizer.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct')` and `AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct')`. This repository records the configuration and exact upstream artifacts for the unchanged-model option permitted by the rulebook. It does not duplicate or fine-tune upstream weights. See `runtime_config.json` for the CPU artifact and checksum. A published model card does not by itself establish a working judging endpoint.

## Limitations

Small-model intent extraction can misread dates or profiles. The application validates dates and activity categories, requests missing location/time information, and rejects invalid output. Suitability rules are prototype heuristics, not clinical guidance. Regional AQI forecasts cannot measure an individual's exposure. Map completeness and API availability limit recommendations. The complete application must be evaluated on varied unseen questions before submission.

## Disclosure

OpenAI Codex was used to help write and test application code. No OpenAI model is called by the running assistant.
