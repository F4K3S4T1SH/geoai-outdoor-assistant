# Laptop hosting for judging

The public connection forwards only the GeoAI HTTP application on localhost port 8000. The model server remains on localhost port 8081. No paid hosting plan is used.

Current endpoint: https://thehun-modem-weight-moving.trycloudflare.com/ask

Current API tester: https://thehun-modem-weight-moving.trycloudflare.com/docs

Verified on 23 October 2026 IST: public `/health` returned HTTP 200 with `model_ready: true`. A POST through the public HTTPS address returned HTTP 200 in 16.56 seconds, comparing 20 place/hour combinations across five venues and declining to recommend unsuitable options. One venue timed out and was disclosed. This single warm-cache test is not a latency or uptime guarantee; it used the public route from this laptop, not an independent external test machine.

## Start

From the project folder in PowerShell, run:

```powershell
./start-public.ps1
```

The script starts the local model and API if needed, creates a temporary Cloudflare Quick Tunnel, and prints the public address. Leave it running. The current address is also recorded in `work/public-host.json` (not committed). Local runtime binaries and weights are deliberately excluded from Git.

This laptop already has cloudflared installed under `runtime/cloudflared/cloudflared.exe`, downloaded from the official Cloudflare release: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe . If recreating the project on another Windows machine, download it into that path, and follow README.md to install the Python environment and model runtime.

The hosting helper prevents automatic system sleep only for its own lifetime. It does not change the saved Windows power plan. Keep the laptop plugged in, the lid open, and internet connected; closing the lid, manual sleep, shutdown, restart or network loss can still interrupt judging. The screen can turn off.

## Check before submitting

Open the printed public URL plus `/health`; it should report `model_ready: true`. Open `/docs` for the API tester. The judge sends HTTP POST requests to `/ask` with JSON such as:

```json
{"question":"Where can I go running tomorrow morning within 5 km of Powai?","latitude":19.1176,"longitude":72.906}
```

Coordinates are optional but help resolve neighbourhoods. Results use live source data and may correctly reject all options. Missing locations return clarification. When another request is running, the server returns HTTP 429 with Retry-After. Requests exceeding 85 seconds return HTTP 504. Individual venues get a 12-second evidence budget, and timed-out venues are disclosed rather than silently treated as suitable.

## Stop

Press Ctrl+C in the hosting terminal, or run:

```powershell
./stop-public.ps1
```

This closes the public tunnel. The supervisor then releases temporary sleep prevention and stops only the model/API processes that it started itself. Local services it reused remain running.

## Important URL limitation

Quick Tunnels have no uptime guarantee, and restarting one assigns a new hostname. Keep the current tunnel running through judging. If it must be restarted, update the submission form and README with the new `/ask` URL before judging. This is a temporary hackathon development endpoint, not permanent hosting.

Cloudflare reference: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
