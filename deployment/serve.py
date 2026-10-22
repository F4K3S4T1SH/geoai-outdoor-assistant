"""Run the API and local CPU model together, with orderly process shutdown."""
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
MODEL=ROOT/'models/qwen2.5-1.5b-instruct-q4_k_m.gguf'
EXPECTED='6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'

def main():
    if not MODEL.exists():
        from huggingface_hub import hf_hub_download
        hf_hub_download('Qwen/Qwen2.5-1.5B-Instruct-GGUF',MODEL.name,
                        revision='91cad51170dc346986eccefdc2dd33a9da36ead9',local_dir=MODEL.parent)
    with MODEL.open('rb') as f:
        digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=EXPECTED: raise RuntimeError('Model checksum does not match official artifact')
    binary=os.environ.get('LLAMA_SERVER','llama-server')
    model=subprocess.Popen([binary,'-m',str(MODEL),'--host','127.0.0.1','--port','8081',
        '-c','4096','-t',os.environ.get('MODEL_THREADS','2'),'--parallel','1'])
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
