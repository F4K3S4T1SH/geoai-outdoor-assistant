import asyncio,json,time,sys,os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from geoai import model
from geoai.intent import normalize
async def main():
 cases=json.loads(Path('tests/intent_cases.json').read_text());results=[]
 now=datetime(2026,10,23,10,tzinfo=ZoneInfo('Asia/Kolkata'))
 for index,case in enumerate(cases):
  t=time.monotonic()
  try:
   raw=await model.extract(case['question'],now.isoformat());parsed=normalize(raw,case['question'],now)
   errors={k:{'expected':v,'actual':parsed.get(k)} for k,v in case['expected'].items() if parsed.get(k)!=v}
   row={'question':case['question'],'passed':not errors,'errors':errors,'parsed':parsed,'raw':raw,'seconds':round(time.monotonic()-t,2)}
  except Exception as exc:row={'question':case['question'],'passed':False,'error':type(exc).__name__+': '+str(exc),'seconds':round(time.monotonic()-t,2)}
  results.append(row);print(f"{index+1}/{len(cases)} {'PASS' if row['passed'] else 'FAIL'} {row.get('errors',row.get('error',''))}",flush=True)
 target=Path(sys.argv[1]);target.write_text(json.dumps({'model':model.MODEL,'passed':sum(x['passed'] for x in results),'total':len(results),'cases':results},indent=2),encoding='utf-8')
 print('Saved',target,flush=True)
asyncio.run(main())
