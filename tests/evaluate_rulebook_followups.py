"""Continue the example-query checks with explicitly recorded test choices."""
import json,time
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx

initial=json.loads(Path('submission/rulebook-query-evaluation.json').read_text(encoding='utf-8'))
base=initial['base_url'];cases={r['number']:r for r in initial['cases']};rows=[]
city={1:'Pune',3:'Mumbai',6:'Mumbai',7:'Mumbai'}
names={1:'Koregaon Park',2:'Whitefield',3:'Powai',5:'Pune',6:'Andheri',7:'Bandra',8:'Lonavala',10:'Hinjawadi'}
tomorrow=(datetime.now(ZoneInfo('Asia/Kolkata'))+timedelta(days=1)).date().isoformat()
with httpx.Client(timeout=100) as client:
    for number in [7,10,1,2,3,5,6,8,9,4]:
        row=cases[number];payload={'question':row['question']};choice={}
        if number in names:
            matches=row['response'].get('matches',[])
            hits=[m for m in matches if m.get('name')==names[number] and m.get('country')=='India' and (number not in city or city[number] in m.get('label',''))]
            if not hits:raise RuntimeError(f'No verified test location for query {number}')
            hit=hits[0];choice={'location':hit,'note':'Test harness selected this matching public map candidate; not a claim that the user confirmed it.'}
            payload.update(latitude=hit['latitude'],longitude=hit['longitude'],location=hit['label'])
        elif number==9:
            payload.update(latitude=12.9763,longitude=77.5929,location='Cubbon Park, Bengaluru',profile='senior')
            choice={'note':'Explicit test choice: senior profile and the public Cubbon Park coordinates verified in earlier live tests. No age or health fact about the user is assumed.'}
        elif number==4:
            payload.update(latitude=12.9763,longitude=77.5929,destination='Vidhana Soudha',destination_latitude=12.9797,destination_longitude=77.5907,start=tomorrow+'T08:00',end=tomorrow+'T09:00')
            choice={'note':'Explicit test origin/destination/date: Cubbon Park to Vidhana Soudha tomorrow at 08:00. These were missing from the original question and are not inferred user addresses.'}
        start=time.monotonic()
        try:
            response=client.post(base+'/ask',json=payload);body=response.json()
            result={'number':number,'test_choice':choice,'payload':payload,'http_status':response.status_code,'seconds':round(time.monotonic()-start,2),'response':body}
            print(number,response.status_code,body.get('status'),body.get('question',body.get('message','')),body.get('compared'),flush=True)
        except Exception as exc:
            result={'number':number,'test_choice':choice,'payload':payload,'error':repr(exc),'seconds':round(time.monotonic()-start,2)}
            print(number,repr(exc),flush=True)
        rows.append(result)
        Path('submission/rulebook-followup-evaluation.json').write_text(json.dumps({'recorded_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'base_url':base,'test_choices_disclosed':True,'cases':rows},indent=2),encoding='utf-8')
