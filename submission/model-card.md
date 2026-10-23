---
license: apache-2.0
base_model: ibm-granite/granite-3.3-2b-instruct
pipeline_tag: text-generation
library_name: llama-cpp-python
language:
  - en
tags:
  - gguf
  - geoai
  - outdoor-planning
---
# NEXA â€” Outside outdoor assistant

Unchanged IBM Granite 3.3 2B Instruct, run locally on CPU using the official IBM Q4_K_M GGUF. **2,533,539,840 actual parameters**, below the strict 3-billion ceiling. The count is the sum of logical dimensions of the 362 GGUF tensors, with tied embeddings stored once. No fine-tuning or adapters were applied by this team. IBM's original instruction tuning is part of the upstream model.

## Provenance and licence

- Base: https://huggingface.co/ibm-granite/granite-3.3-2b-instruct
- Base revision: `707f574c62054322f6b5b04b6d075f0a8f05e0f0`
- GGUF: `ibm-granite/granite-3.3-2b-instruct-GGUF`
- GGUF revision: `7cdf86ccd1f1bb3491c9b7017b033f2e51367397`
- File: `granite-3.3-2b-instruct-Q4_K_M.gguf`
- SHA256: `ac71e9e32c0bea919b409c5918f69ca74339854b0319c5065e4e9fb6d95c4852`
- Apache 2.0; original IBM weights and accompanying tokenizer/configuration are unchanged. See LICENSE and NOTICE.

This repository includes actual quantized weights, matching upstream configuration/tokenizer, and the application's runtime configuration. Earlier repository revisions used Qwen2.5 1.5B; current inference uses Granite only.

## Load with from_pretrained

Use the quantized loader to fit a laptop. Install `llama-cpp-python` and `huggingface_hub`, then:

```python
from llama_cpp import Llama
llm = Llama.from_pretrained(
    repo_id="F4K3S4T1SH/geoai-outdoor-model",
    filename="granite-3.3-2b-instruct-Q4_K_M.gguf",
    n_ctx=4096, n_threads=8, verbose=False,
)
answer = llm.create_chat_completion(
    messages=[{"role":"user", "content":"Reply with OK."}],
    max_tokens=8, temperature=0,
)
print(answer["choices"][0]["message"]["content"])
```

The public repository is a GGUF package, not a safetensors checkpoint. Use the explicit quantized loader above. The unquantized Transformers base can be loaded from IBM's pinned base repository; it needs more memory. This does not require a hosted inference service.

This loader was verified on the public repository at revision `565b78d00f7198c84c3aa8f616a4f2ce06422ff9` with llama-cpp-python 0.3.36 and produced `OK.`. Public LFS SHA256 was checked first; the identical official file was reused in the local Hub cache to avoid a duplicate download. See `submission/model-loading-check.json` in the code repository.

## Intended use

The application asks the model to extract activity, place, dates and profile as schema-constrained JSON. Generic validation enforces explicit dates, age/profile words, exercise distance, missing addresses and clear activity words. After fetching live map/weather/AQI evidence and filtering the full activity duration, the model compares only supplied eligible candidates and cites permitted evidence keys. Code validates the selection and renders fetched values. No weather or place facts come from model memory. Reasoning/thinking is disabled for bounded CPU latency; context is 4096 and temperature is zero.

Application, evaluation and loading reports: https://github.com/F4K3S4T1SH/geoai-outdoor-assistant . Development fixtures are not runtime answers. Intended for an English-language hackathon prototype; unseen questions can still be misread. The live API asks for clarification or reports missing sources rather than fabricating a plan.

## Limitations and disclosure

Regional forecasts, incomplete maps and provider outages limit recommendations. Suitability thresholds are transparent prototype heuristics, not clinical validation. Traffic is a road/time proxy, not live congestion. Exercise courses, venue hours/access and ground conditions are unverified. The laptop endpoint has no uptime guarantee.

OpenAI Codex helped write and test the application; no OpenAI or other hosted large model is called by the running assistant. Team NEXA, account F4K3S4T1SH. Application code is MIT; model/data licences remain separate.
