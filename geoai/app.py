import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from . import data, model
from .intent import normalize
from .ranking import ACTIVITIES, suitable, context_features, score

app=FastAPI(title='GeoAI Outdoor Assistant',version='0.1.0')
TZ=ZoneInfo('Asia/Kolkata')
GATE=asyncio.Semaphore(1)

class Query(BaseModel):
    question: str=Field(min_length=3,max_length=1500)
    latitude: float|None=Field(default=None,ge=-90,le=90)
    longitude: float|None=Field(default=None,ge=-180,le=180)

@app.get('/')
def home():
    return {'project':'GeoAI Outdoor Assistant','interactive_api':'/docs','status':'development'}

@app.get('/health')
async def health():
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r=await c.get('http://127.0.0.1:8081/health')
        ready=r.status_code==200
    except httpx.HTTPError: ready=False
    return {'api':'ok','model_ready':ready,'model':model.MODEL}

@app.get('/activities')
def activities(): return list(ACTIVITIES)

@app.post('/ask')
async def ask(q:Query):
    try: await asyncio.wait_for(GATE.acquire(),timeout=1)
    except TimeoutError: raise HTTPException(429,detail='The laptop is answering another question. Please retry shortly.',headers={'Retry-After':'10'})
    try:
        try:
            async with asyncio.timeout(85): return await recommend(q)
        except TimeoutError: raise HTTPException(504,detail='Live data collection exceeded the request time limit. Please retry; no results were invented.')
        except data.SourceError as e: raise HTTPException(503,detail={'status':'source_unavailable','message':str(e)})
        except httpx.HTTPError as e: raise HTTPException(503,detail='Local small model unavailable or timed out') from e
        except (ValueError,KeyError,TypeError) as e:
            raise HTTPException(422,detail='Could not interpret the request. Please specify activity, place and dates clearly.') from e
    finally: GATE.release()

async def venue_evidence(place):
    weather,ws=await data.forecast(place['lat'],place['lon'])
    sources=[ws]; failures=[]
    try:
        aq,aas=await data.air(place['lat'],place['lon']); sources.append(aas)
        aqmap=dict(zip(aq['hourly']['time'],aq['hourly']['us_aqi']))
    except data.SourceError:
        aqmap={}; failures.append('Air quality unavailable for '+place['name'])
    ctx,cs=await data.context(place['lat'],place['lon']); sources.append(cs)
    return weather,aqmap,ctx,sources,failures

async def recommend(q):
    now=datetime.now(TZ)
    intent=normalize(await model.extract(q.question,now.isoformat()),q.question,now)
    activity=intent.get('activity'); location=intent.get('location'); profile=intent.get('profile','general')
    if activity not in ACTIVITIES:
        return {'status':'clarification_needed','question':'Which outdoor activity would you like to do?','supported_activities':list(ACTIVITIES)}
    if (q.latitude is None)!=(q.longitude is None):
        return {'status':'clarification_needed','question':'Please provide both latitude and longitude.'}
    sources=[]
    if q.latitude is not None: lat,lon=q.latitude,q.longitude
    elif not location: return {'status':'clarification_needed','question':'Which neighbourhood or city should I search near?'}
    else:
        geo,src=await data.geocode(location); sources.append(src)
        hits=geo.get('results',[])
        if len(hits)!=1:
            return {'status':'clarification_needed','question':'Please confirm the location using coordinates, or give a more specific place name.',
                    'matches':hits,'sources':sources}
        lat,lon=hits[0]['latitude'],hits[0]['longitude']
    if not intent.get('start') or not intent.get('end'):
        return {'status':'clarification_needed','question':'What date and time range should I compare?','parsed_request':intent}
    start=datetime.fromisoformat(intent['start']); end=datetime.fromisoformat(intent['end'])
    start=start.replace(tzinfo=TZ) if start.tzinfo is None else start.astimezone(TZ)
    end=end.replace(tzinfo=TZ) if end.tzinfo is None else end.astimezone(TZ)
    start=max(start,now)
    if end<=start or end>now+timedelta(days=5):
        return {'status':'clarification_needed','question':'Please choose a future interval within the next five days.'}
    radius=float(intent.get('radius_km') or 10)
    if not 0<radius<=40:
        return {'status':'clarification_needed','question':'Please choose a search radius between 1 and 40 km.'}
    if profile not in ('general','asthma','senior','child','pregnancy'): profile='general'
    found,src=await data.places(lat,lon,radius); sources.append(src)
    venues=[p for p in found if suitable(p,activity)][:5]
    if not venues:
        return {'status':'no_verified_venues','message':'No named compatible venues found in the live map query. Try a wider radius or different location.', 'sources':sources}
    options=[]; failures=[]
    for place in venues:
        try:
            weather,aqmap,ctx,ss,ff=await asyncio.wait_for(venue_evidence(place),timeout=12)
            sources.extend(ss); failures.extend(ff)
            h=weather['hourly']
            for i,t in enumerate(h['time']):
                dt=datetime.fromisoformat(t).replace(tzinfo=TZ)
                if not start<=dt<=end: continue
                w={k:v[i] for k,v in h.items() if k!='time'}
                features=context_features(place,ctx.get('elements',[]),w.get('wind_direction_10m'))
                value,blockers,reasons=score(activity,profile,w,aqmap.get(t),features)
                options.append({'place':place,'time':dt.isoformat(),'score':value,'avoid_reasons':blockers,
                                'tradeoffs':reasons,'weather':w,'us_aqi':aqmap.get(t),'geographic_context':features})
        except (data.SourceError,TimeoutError): failures.append('Live data unavailable or timed out for '+place['name'])
    valid=sorted([o for o in options if o['score'] is not None and not o['avoid_reasons']],key=lambda o:(-o['score'],o['place']['distance_km'],o['time']))
    best=valid[0] if valid else None
    model_evidence={}
    if valid:
        shortlist=[]; seen=set()
        for o in valid:
            key=o['place'].get('id',o['place']['name'])
            if key not in seen: shortlist.append(o); seen.add(key)
            if len(shortlist)==5: break
        chosen,model_evidence=await model.choose(shortlist,activity,profile)
        best=shortlist[chosen]
    advice=['Carry drinking water and sun protection.','Check venue access and opening hours directly before leaving.']
    if activity in ('cycling','hiking'): advice.append('Check the route and appropriate protective equipment before departure.')
    return {'status':'recommendation' if best else 'avoid_or_insufficient_data',
            'request':intent,'search_center':{'latitude':lat,'longitude':lon},'best':best,
            'alternatives':[o for o in valid if o is not best][:3], 'model_reasoning_evidence':model_evidence,
            'summary':(f"Consider {best['place']['name']} at {best['time']}. Forecast apparent temperature {best['weather']['apparent_temperature']} C, rain probability {best['weather']['precipitation_probability']}%, wind {best['weather']['wind_speed_10m']} km/h, US AQI {best['us_aqi']}." if best else 'No compared place/time passed all checks, or evidence was incomplete.'),
            'avoided_options':sorted([o for o in options if o['avoid_reasons']],key=lambda o:o['time'])[:5],
            'compared':{'venues':len(venues),'place_hour_pairs':len(options)},'advice':advice,
            'sources':sources,'data_failures':failures,
            'limitations':['Prototype suitability scores are configurable heuristics, not medical advice or a safety guarantee.',
                'AQI is a regional model forecast, not street-level measurement. US AQI scale is used.',
                'Road and industry wind alignment is an exposure proxy, not a pollution concentration estimate.',
                'Map coverage, access and opening hours may be incomplete. No live traffic or travel time is available.',
                'At most the five nearest compatible named venues are compared. Hourly windows do not verify full activity duration.'],
            'attribution':['© OpenStreetMap contributors','Weather: Open-Meteo','Air quality: CAMS via Open-Meteo','Geocoding: GeoNames via Open-Meteo'],
            'model':model.MODEL,'generated_at':datetime.now(TZ).isoformat()}
