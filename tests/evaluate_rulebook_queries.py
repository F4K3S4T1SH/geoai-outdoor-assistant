"""Run the PDF's ten input examples unchanged against the live public API.

These questions are test inputs only, never runtime response templates.
"""
import json,time,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx

base=sys.argv[1].rstrip('/') if len(sys.argv)>1 else json.loads(Path('work/public-host.json').read_text())['url']
questions=json.loads(Path('tests/rulebook_queries.json').read_text(encoding='utf-8'))
rows=[]
with httpx.Client(timeout=100) as client:
    for number,question in enumerate(questions,1):
        start=time.monotonic()
        try:
            response=client.post(base+'/ask',json={'question':question})
            body=response.json()
            row={'number':number,'question':question,'http_status':response.status_code,'seconds':round(time.monotonic()-start,2),'response':body}
            print(number,response.status_code,body.get('status'),body.get('field'),body.get('question',body.get('message','')),flush=True)
            if body.get('parsed_request'):print('INTENT',json.dumps(body['parsed_request']),flush=True)
            if body.get('matches'):print('MATCHES',json.dumps(body['matches']),flush=True)
        except Exception as exc:
            row={'number':number,'question':question,'error':repr(exc),'seconds':round(time.monotonic()-start,2)}
            print(number,repr(exc),flush=True)
        rows.append(row)
        Path('submission/rulebook-query-evaluation.json').write_text(json.dumps({'recorded_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'base_url':base,'questions_sent_unchanged':True,'cases':rows},indent=2),encoding='utf-8')
