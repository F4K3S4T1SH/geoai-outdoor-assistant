"""Download the pinned open model and verify its bytes before use.

Run from the repository root: python deployment/download_model.py
"""
import hashlib
import json
from pathlib import Path
from huggingface_hub import hf_hub_download

ROOT=Path(__file__).resolve().parents[1]

def main():
    config=json.loads((ROOT/'submission/runtime_config.json').read_text(encoding='utf-8'))
    if not 0<config['parameter_count']<=3_000_000_000:
        raise RuntimeError('Model does not satisfy the rulebook size limit')
    path=Path(hf_hub_download(config['gguf_repo'],config['gguf_file'],
        revision=config['gguf_revision'],local_dir=ROOT/'models'))
    with path.open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=config['sha256']: raise RuntimeError('Model checksum mismatch')
    print('Pinned model downloaded and SHA256 verified:',path.name)

if __name__=='__main__': main()
