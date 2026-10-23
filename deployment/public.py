"""Laptop hosting supervisor. Only the application API is forwarded publicly."""
from contextlib import ExitStack
import ctypes
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work'

def ready(url,model=False):
    try:
        r=httpx.get(url,timeout=3)
        return r.status_code==200 and (not model or r.json().get('model_ready') is True)
    except (httpx.HTTPError,ValueError): return False

def main():
    os.chdir(ROOT); WORK.mkdir(exist_ok=True)
    tunnel=ROOT/'runtime/cloudflared/cloudflared.exe'
    config=json.loads((ROOT/'submission/runtime_config.json').read_text(encoding='utf-8'))
    if config['parameter_count']>3_000_000_000: raise RuntimeError('Model exceeds rulebook size limit')
    weights=ROOT/'models'/config['gguf_file']
    model_name=config['base_model'].split('/')[-1]
    llama=ROOT/'runtime/llama/llama-server.exe'
    if not all(p.exists() for p in (tunnel,weights,llama)):
        raise RuntimeError('Local tunnel runtime, model runtime or weights are missing. See README.')
    own=[]; state=WORK/'public-host.json'
    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with ExitStack() as stack:
        def spawn(cmd,log):
            f=stack.enter_context((WORK/log).open('wb'))
            p=subprocess.Popen(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,creationflags=creationflags)
            own.append(p); return p
        try:
            model_proc=None; api_proc=None
            if ready('http://127.0.0.1:8081/health'):
                loaded=httpx.get('http://127.0.0.1:8081/v1/models',timeout=3).json()
                if not any(item.get('id')==model_name for item in loaded.get('data',[])):
                    raise RuntimeError('A different model occupies port 8081. Stop it before starting this configuration.')
            if not ready('http://127.0.0.1:8081/health'):
                model_proc=spawn([str(llama),'-m',str(weights),'--host','127.0.0.1','--port','8081','-c',str(config.get('context_length',4096)),'-t','8','--parallel','1','--alias',model_name,'--reasoning-budget','0','--reasoning','off'],'public-model.log')
                for _ in range(90):
                    if ready('http://127.0.0.1:8081/health'): break
                    time.sleep(1)
                else: raise RuntimeError('Model did not become ready')
            if not ready('http://127.0.0.1:8000/health',model=True):
                api_proc=spawn([sys.executable,'-m','uvicorn','geoai.app:app','--host','127.0.0.1','--port','8000'],'public-api.log')
                for _ in range(30):
                    if ready('http://127.0.0.1:8000/health',model=True): break
                    time.sleep(1)
                else: raise RuntimeError('API did not become ready')
            if os.name=='nt':
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
            proc=spawn([str(tunnel),'tunnel','--no-autoupdate','--protocol','http2','--url','http://127.0.0.1:8000'],'public-tunnel.log')
            url=None
            for _ in range(120):
                if proc.poll() is not None: raise RuntimeError('Tunnel stopped; see work/public-tunnel.log')
                text=(WORK/'public-tunnel.log').read_text(encoding='utf8',errors='replace')
                match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',text)
                if match: url=match.group(); break
                time.sleep(1)
            if not url: raise RuntimeError('No public URL was assigned; see work/public-tunnel.log')
            state.write_text(json.dumps({'url':url,'ask_endpoint':url+'/ask','tunnel_pid':proc.pid,
                'supervisor_pid':os.getpid(),'created_at':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf8')
            print('Public API: '+url+'/ask',flush=True)
            print('API tester: '+url+'/docs',flush=True)
            print('Keep the laptop plugged in, connected, and the lid open. Automatic sleep is prevented only while this process runs.',flush=True)
            print('Press Ctrl+C or run stop-public.ps1 to close the public connection.',flush=True)
            restarts=0
            while proc.poll() is None:
                time.sleep(3)
                if model_proc is not None and model_proc.poll() is not None:
                    if restarts>=3: raise RuntimeError('Model repeatedly stopped; see public-model.log')
                    model_proc=spawn([str(llama),'-m',str(weights),'--host','127.0.0.1','--port','8081','-c',str(config.get('context_length',4096)),'-t','8','--parallel','1','--alias',model_name,'--reasoning-budget','0','--reasoning','off'],'public-model.log'); restarts+=1
                if api_proc is not None and api_proc.poll() is not None:
                    if restarts>=3: raise RuntimeError('API repeatedly stopped; see public-api.log')
                    api_proc=spawn([sys.executable,'-m','uvicorn','geoai.app:app','--host','127.0.0.1','--port','8000'],'public-api.log'); restarts+=1

        except KeyboardInterrupt: pass
        finally:
            for p in reversed(own):
                if p.poll() is None:
                    p.terminate()
                    try: p.wait(timeout=8)
                    except subprocess.TimeoutExpired: p.kill(); p.wait()
            if os.name=='nt': ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            if state.exists(): state.unlink()

if __name__=='__main__': main()
