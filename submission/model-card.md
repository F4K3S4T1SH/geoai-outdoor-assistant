---
license: apache-2.0
base_model: Qwen/Qwen2.5-1.5B-Instruct
pipeline_tag: text-generation
language:
  - en
tags:
  - geoai
  - outdoor-planning
  - small-language-model
---
# GeoAI Outdoor Assistant — Qwen 1.5B GGUF

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

This repository includes the actual official GGUF weights, upstream tokenizer/configuration, an Apache 2.0 licence and attribution. The weights are unchanged from the upstream quantized artifact. No fine-tuning is claimed.

For laptop-friendly loading, the tested `from_pretrained` path is:

```python
from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id='F4K3S4T1SH/geoai-outdoor-model',
    filename='qwen2.5-1.5b-instruct-q4_k_m.gguf',
    n_ctx=4096,
    verbose=False,
)
```

This was actually loaded with llama-cpp-python 0.3.36 and generated `OK` in a smoke test. The report is in the code repository at `submission/model-loading-check.json`. The public LFS SHA256 was verified, then the identical official file was reused through a local Hub cache to avoid a duplicate download.

Transformers also documents this explicit GGUF loading path:

```python
from transformers import AutoTokenizer, AutoModelForCausalLM

repo = 'F4K3S4T1SH/geoai-outdoor-model'
filename = 'qwen2.5-1.5b-instruct-q4_k_m.gguf'
tokenizer = AutoTokenizer.from_pretrained(repo, gguf_file=filename)
model = AutoModelForCausalLM.from_pretrained(repo, gguf_file=filename)
```

This alternative requires PyTorch, Transformers and GGUF support. The explicit `gguf_file` argument is required: the repository contains GGUF, not a Transformers safetensors checkpoint. The Qwen2 GGUF loader dequantizes weights. It was not executed on this laptop because there was insufficient free memory for full dequantization while hosting the app. Use the tested quantized loader above for laptop verification. See https://huggingface.co/docs/transformers/quantization/gguf .

The same original base remains available at `Qwen/Qwen2.5-1.5B-Instruct`. See `runtime_config.json` for provenance and the exact checksum. Publication of weights does not establish judging-window uptime.

## Limitations

Small-model intent extraction can misread dates or profiles. The application validates dates and activity categories, requests missing location/time information, and rejects invalid output. Suitability rules are prototype heuristics, not clinical guidance. Regional AQI forecasts cannot measure an individual's exposure. Map completeness and API availability limit recommendations. The complete application must be evaluated on varied unseen questions before submission.

## Disclosure

OpenAI Codex was used to help write and test application code. No OpenAI model is called by the running assistant.
