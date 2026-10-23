"""Run the API and local CPU model together, with orderly process shutdown."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
CONFIG=json.loads((ROOT/'submission/runtime_config.json').read_text(encoding='utf-8'))
if not 0<CONFIG['parameter_count']<=3_000_000_000:
    raise RuntimeError('Model must satisfy the rulebook parameter limit')
MODEL=ROOT/'models'/CONFIG['gguf_file']
EXPECTED=CONFIG['sha256']

def main():
    if not MODEL.exists():
        from huggingface_hub import hf_hub_download
        hf_hub_download(CONFIG['gguf_repo'],MODEL.name,
                        revision=CONFIG['gguf_revision'],local_dir=MODEL.parent)
    with MODEL.open('rb') as f:
        digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=EXPECTED: raise RuntimeError('Model checksum does not match official artifact')
    binary=os.environ.get('LLAMA_SERVER','llama-server')
    model=subprocess.Popen([binary,'-m',str(MODEL),'--host','127.0.0.1','--port','8081',
        '-c',str(CONFIG['context_length']),'-t',os.environ.get('MODEL_THREADS','2'),'--parallel','1',
        '--alias',CONFIG['base_model'].split('/')[-1],'--reasoning','off','--reasoning-budget','0'])
    api=None
    def stop(*_):
        for p in (api,model):
            if p is not None and p.poll() is None: p.terminate()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        for _ in range(120):
            if model.poll() is not None: raise RuntimeError('Local model server stopped during startup')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8081/health',timeout=2) as r:
                    if r.status==200: break
            except OSError: time.sleep(1)
        else: raise RuntimeError('Model startup timed out')
        api=subprocess.Popen([sys.executable,'-m','uvicorn','geoai.app:app','--host','0.0.0.0',
                              '--port',os.environ.get('PORT','7860')])
        while model.poll() is None and api.poll() is None: time.sleep(1)
    finally:
        stop()
        for p in (api,model):
            if p is not None:
                try: p.wait(timeout=10)
                except subprocess.TimeoutExpired: p.kill(); p.wait()

if __name__=='__main__': main()
