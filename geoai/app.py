import asyncio,math,time
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Literal
import httpx
from fastapi import FastAPI,HTTPException,Query as Param
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from . import data,model
from .intent import normalize
from .ranking import ACTIVITIES,suitable,context_features,score,valid_number
from .advice import advice_for

app=FastAPI(title='GeoAI Outdoor Assistant',version='0.4.0')
TZ=ZoneInfo('Asia/Kolkata'); GATE=asyncio.Semaphore(1)
STATIC=Path(__file__).resolve().parent/'static'
STATIC.mkdir(exist_ok=True)
app.mount('/assets',StaticFiles(directory=STATIC),name='assets')
Activity=Literal['running','cycling','golf','cricket','football','tennis','hiking','picnic','event','photography']
Profile=Literal['general','asthma','senior','child','pregnancy']

class Query(BaseModel):
    question:str=Field(min_length=3,max_length=1500)
    latitude:float|None=Field(default=None,ge=-90,le=90)
    longitude:float|None=Field(default=None,ge=-180,le=180)
    location:str|None=Field(default=None,max_length=160)
    activity:Activity|None=None
    profile:Profile|None=None
    radius_km:float|None=Field(default=None,gt=0,le=40)
    start:datetime|None=None
    end:datetime|None=None
    duration_minutes:int|None=Field(default=None,ge=1,le=360)
    exercise_distance_km:float|None=Field(default=None,gt=0,le=200)
    pace_minutes_per_km:float|None=Field(default=None,ge=2,le=30)
    venue_scope:Literal['exact','nearby']|None=None
    venue_id:str|None=Field(default=None,pattern=r'^(node|way|relation)/[0-9]+$')
    destination:str|None=Field(default=None,max_length=160)
    destination_latitude:float|None=Field(default=None,ge=-90,le=90)
    destination_longitude:float|None=Field(default=None,ge=-180,le=180)
    mode:Literal['leisure','commute']|None=None
    max_travel_minutes:int|None=Field(default=None,ge=5,le=180)

@app.get('/',include_in_schema=False)
def home(): return FileResponse(STATIC/'index.html')

@app.get('/health')
async def health():
    try:
        async with httpx.AsyncClient(timeout=3) as c: r=await c.get('http://127.0.0.1:8081/health')
        ready=r.status_code==200
        if ready:
            async with httpx.AsyncClient(timeout=3) as c: names=await c.get('http://127.0.0.1:8081/v1/models')
            ready=names.status_code==200 and any(m.get('id')==model.MODEL for m in names.json().get('data',[]))
    except (httpx.HTTPError,ValueError,AttributeError,TypeError): ready=False
    return {'api':'ok','model_ready':ready,'model':model.MODEL,'version':'0.4.0'}

@app.get('/activities')
def activities(): return list(ACTIVITIES)

@app.get('/locations')
async def locations(q:str=Param(min_length=3,max_length=160)):
    try:
        result,source=await data.geocode(q)
        return {'matches':result.get('results',[]),'source':source}
    except data.SourceError as e: raise HTTPException(503,detail='Place search is unavailable. Retry or enter coordinates.') from e

@app.post('/ask')
async def ask(q:Query):
    try: await asyncio.wait_for(GATE.acquire(),timeout=1)
    except TimeoutError: raise HTTPException(429,detail='The laptop is answering another question. Please retry shortly.',headers={'Retry-After':'10'})
    try:
        try:
            async with asyncio.timeout(85): return await recommend(q)
        except TimeoutError: raise HTTPException(504,detail='Live data collection exceeded the request time limit. Please retry; no results were invented.')
        except data.SourceError as e: raise HTTPException(503,detail={'status':'source_unavailable','message':str(e)})
        except model.ModelError as e: return clarify('The small model could not finish understanding this request. Please select the activity, place and dates in the form and retry.',field='model')
        except httpx.HTTPError as e: raise HTTPException(503,detail='The local small model is unavailable or timed out.') from e
        except (ValueError,KeyError,TypeError) as e: raise HTTPException(422,detail='Please confirm the activity, place and dates using the form.') from e
    finally: GATE.release()

def clarify(question,intent=None,**extra): return {'status':'clarification_needed','question':question,'parsed_request':intent or {},**extra}
def local(dt): return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)

async def resolve(name,sources):
    result,source=await data.geocode(name); sources.append(source); hits=result.get('results',[])
    return (hits[0],None) if len(hits)==1 else (None,hits)

async def venue_evidence(place):
    results=await asyncio.gather(data.forecast(place['lat'],place['lon']),data.air(place['lat'],place['lon']),data.context(place['lat'],place['lon']),return_exceptions=True)
    if isinstance(results[0],Exception): raise data.SourceError('Required weather unavailable')
    weather,ws=results[0]; sources=[ws]; failures=[]
    h=weather.get('hourly',{})
    if not isinstance(h.get('time'),list) or not h['time'] or any(not isinstance(v,list) or len(v)!=len(h['time']) for v in h.values()): raise data.SourceError('Weather source returned an incomplete hourly series')
    for key,values in h.items():
        if key!='time': h[key]=[v if valid_number(v) else None for v in values]
    if isinstance(results[2],Exception):
        ctx={'elements':[],'context_available':False}; failures.append('Geographic context unavailable for '+place['name']+'; no positive recommendation can be made')
    else:
        ctx,cs=results[2]; sources.append(cs)
    if isinstance(results[1],Exception): aqmap={}; failures.append('Air quality unavailable for '+place['name'])
    else:
        aq,aas=results[1]; sources.append(aas); aqmap={t:(v if valid_number(v,0,500) else None) for t,v in zip(aq.get('hourly',{}).get('time',[]),aq.get('hourly',{}).get('us_aqi',[]))}
    return weather,aqmap,ctx,sources,failures

async def route_evidence(origin,place,activity):
    try: return await asyncio.wait_for(data.route(origin,(place['lat'],place['lon']),'bicycle' if activity=='cycling' else 'pedestrian'),timeout=7)
    except (data.SourceError,TimeoutError,ValueError): return None,None

async def recommend(q):
    begun=time.monotonic(); now=datetime.now(TZ); intent=normalize(await model.extract(q.question,now.isoformat()),q.question,now)
    for key in ('activity','profile','radius_km','location','duration_minutes','destination','mode','exercise_distance_km','pace_minutes_per_km','venue_scope','max_travel_minutes'):
        value=getattr(q,key)
        if value is not None: intent[key]=value
    if q.start is not None: intent['start']=local(q.start).isoformat(); intent.pop('hours',None); intent.pop('sunset_only',None)
    if q.end is not None: intent['end']=local(q.end).isoformat()
    if intent.get('out_of_scope') is True and q.activity is not None: return clarify('Your question describes an unsupported task or indoor activity. Please edit it to describe the outdoor activity selected in the form.',intent,field='activity')
    if intent.get('out_of_scope') is True: return {'status':'out_of_scope','message':'I can help compare outdoor places and times. Choose an outdoor activity to begin.','supported_activities':list(ACTIVITIES)}
    activity=intent.get('activity'); profile=intent.get('profile','general'); location=intent.get('location')
    if activity not in ACTIVITIES: return clarify('Which outdoor activity would you like to do?',intent,supported_activities=list(ACTIVITIES))
    if profile not in ('general','asthma','senior','child','pregnancy'): return clarify('Please confirm a personal profile in the form.',intent)
    if (q.latitude is None)!=(q.longitude is None): return clarify('Please provide both latitude and longitude.',intent)
    if intent.get('invalid_age'): return clarify('Please confirm the age; use a value from 0 to 120.',intent,field='profile')
    if intent.get('confirm_family_profile') and q.profile is None: return clarify('What age group or health considerations apply to your parents/family? Select a profile, or state their ages; I will not assume they are seniors.',intent,field='profile')
    distance=intent.get('exercise_distance_km')
    if activity=='cycling' and intent.get('mode')=='commute' and (distance is not None or intent.get('venue_scope')=='exact'):
        return clarify('A commute assesses a route to a destination. For a distance target inside one venue, choose a leisure ride; for a commute, choose nearby places and clear the exercise-distance target.',intent,field='exercise_distance_km')
    if distance is not None:
        distance=float(distance)
        if not math.isfinite(distance) or not 0<distance<=200: return clarify('Choose an exercise distance greater than zero and no more than 200 km.',intent,field='exercise_distance_km')
        if activity not in ('running','hiking','cycling'): return clarify('Exercise distance applies to running, walking/hiking or cycling. Please check the activity.',intent)
        pace=intent.get('pace_minutes_per_km')
        if q.duration_minutes is None and not intent.get('duration_explicit'):
            if pace is None: return clarify(f'{distance:g} km is your exercise distance, not a search radius. How long do you expect it to take? Enter an activity duration or your pace in minutes per km.',intent,field='duration')
            pace=float(pace)
            if not math.isfinite(pace) or not 2<=pace<=30: return clarify('Enter a pace between 2 and 30 minutes per km, or supply an expected duration.',intent,field='duration')
            intent['duration_minutes']=math.ceil(distance*pace); intent['duration_basis']='Exercise distance × your supplied pace'
        else: intent['duration_basis']='Your supplied expected duration'
    else: intent['duration_basis']='Your supplied duration' if q.duration_minutes is not None or intent.get('duration_explicit') else 'Default one-hour activity'
    sources=[]; selected_venue=None
    if intent.get('venue_scope')=='exact':
        venue_id=q.venue_id
        if not venue_id:
            if not location: return clarify('Find and confirm the specific venue you want to use.',intent,field='location')
            hit,matches=await resolve(location,sources)
            if hit is None: return clarify('You asked to stay at a specific venue. Please confirm that exact mapped place; I will not substitute nearby parks.',intent,matches=matches,sources=sources,field='location')
            venue_id=hit.get('venue_id')
        if not venue_id: return clarify('This result identifies an area rather than a verified venue. Confirm a mapped park, or choose nearby places.',intent,field='location')
        try: selected_venue,source=await data.venue(venue_id); sources.append(source)
        except (data.SourceError,TimeoutError): return {'status':'insufficient_data','message':'The selected venue could not be verified. Please retry or confirm its mapped identity; no other park was substituted.','request':intent,'sources':sources}
        if selected_venue['tags'].get('access') in ('private','no') or not suitable(selected_venue,activity): return {'status':'no_verified_venues','message':'The selected mapped place is not verified as an accessible outdoor venue for this activity. No nearby park was substituted.','request':intent,'sources':sources}
        lat,lon=selected_venue['lat'],selected_venue['lon']
    elif q.latitude is not None: lat,lon=q.latitude,q.longitude
    elif not location: return clarify('Which neighbourhood or city should I search near?',intent,field='location')
    else:
        hit,matches=await resolve(location,sources)
        if hit is None: return clarify('Please confirm the exact place from these matches, or enter coordinates.',intent,matches=matches,sources=sources,field='location')
        lat,lon=hit['latitude'],hit['longitude']
    if not intent.get('start') or not intent.get('end'): return clarify('What date and time range should I compare?',intent,field='time')
    start=local(datetime.fromisoformat(intent['start'])); end=local(datetime.fromisoformat(intent['end'])); start=max(start,now)
    if end<=start or end>now+timedelta(days=5): return clarify('Choose a future interval within the next five days.',intent,field='time')
    radius=float(intent.get('radius_km') or 10)
    if not math.isfinite(radius) or not 0<radius<=40: return clarify('Choose a search radius from 1 to 40 km.',intent)
    duration=int(intent.get('duration_minutes') if intent.get('duration_minutes') is not None else 60)
    if not 1<=duration<=360: return clarify('Choose a duration from one minute to six hours.',intent)
    if intent.get('max_travel_minutes') is not None and not 5<=intent['max_travel_minutes']<=180:
        return clarify('Choose a travel-time budget from five minutes to three hours.',intent,field='max_travel_minutes')
    if (end-start).total_seconds()<duration*60: return clarify('Widen the time range to fit the full activity duration.',intent,field='time')
    commute=activity=='cycling' and intent.get('mode')=='commute'
    if commute:
        if (q.destination_latitude is None)!=(q.destination_longitude is None): return clarify('Please provide both destination coordinates.',intent,field='destination')
        if q.destination_latitude is not None: dest={'latitude':q.destination_latitude,'longitude':q.destination_longitude,'name':intent.get('destination') or 'Selected destination'}
        elif intent.get('destination') and intent['destination']!='null':
            dest,matches=await resolve(intent['destination'],sources)
            if dest is None: return clarify('Please confirm the commute destination.',intent,matches=matches,sources=sources,field='destination')
        else: return clarify('Where are you cycling to? Confirm the destination in the form.',intent,field='destination')
        route,rs=await route_evidence((lat,lon),{'lat':dest['latitude'],'lon':dest['longitude']},activity)
        if route is None: return {'status':'insufficient_data','message':'I could not verify a bicycle route to this destination. Please retry.','sources':sources}
        sources.append(rs); duration=max(15,math.ceil(route['duration_minutes'])); coords=route['geometry']['coordinates']; mid=coords[len(coords)//2] if coords else [lon,lat]
        venues=[{'id':'selected-destination','name':dest['name'],'lat':mid[1],'lon':mid[0],'destination':{'latitude':dest['latitude'],'longitude':dest['longitude']},'tags':{'bicycle':'designated'},'distance_km':data.distance((lat,lon),(dest['latitude'],dest['longitude'])),'url':f"https://www.openstreetmap.org/?mlat={dest['latitude']}&mlon={dest['longitude']}",'route':route}]
    elif selected_venue is not None:
        venues=[selected_venue]
    else:
        found,src=await data.places(lat,lon,radius,activity); sources.append(src); venues=[p for p in found if suitable(p,activity)][:5]
    if not venues: return {'status':'no_verified_venues','message':'No compatible outdoor venues were verified in the available live map coverage. Source limitations may hide valid venues; inspect the evidence or try another area.','sources':sources,'request':intent}
    options=[]; failures=[]; evaluated=set(); complete=set()
    for venue_index,place in enumerate(venues):
        budget=72-(time.monotonic()-begun)
        if budget<3:
            failures.extend('Not assessed within the request budget: '+p['name'] for p in venues[venue_index:]); break
        try:
            weather,aqmap,ctx,ss,ff=await asyncio.wait_for(venue_evidence(place),timeout=min(14,budget)); sources.extend(ss); failures.extend(ff)
            route=place.get('route')
            if route is None and selected_venue is None and activity in ('cycling','hiking','running'):
                route,rs=await route_evidence((lat,lon),place,activity)
                if rs: sources.append(rs); ss.append(rs)
            if activity=='cycling' and selected_venue is None and route is None: failures.append('No verified bicycle route for '+place['name']); continue
            if route: route={**route,'purpose':'commute' if commute else 'travel_to_venue','duration_basis':'Transport estimate; not exercise duration or a running route'}
            h=weather['hourly']; evaluated.add(place.get('id',place['name'])); times=[local(datetime.fromisoformat(t)) for t in h['time']]
            daily=weather.get('daily',{}); sunrises=dict(zip(daily.get('time',[]),daily.get('sunrise',[]))); sunsets=dict(zip(daily.get('time',[]),daily.get('sunset',[])))
            for i,hour_start in enumerate(times):
                dt=hour_start
                if intent.get('sunset_only'):
                    sunset=sunsets.get(dt.date().isoformat())
                    if not sunset: continue
                    desired=local(datetime.fromisoformat(sunset))-timedelta(minutes=duration*.75)
                    if desired.replace(minute=0,second=0,microsecond=0)!=hour_start: continue
                    dt=desired
                if dt<start or dt+timedelta(minutes=duration)>end: continue
                if intent.get('hours') and not intent['hours'][0]<=dt.hour<intent['hours'][1]: continue
                if intent.get('hours') and dt.hour+duration/60>intent['hours'][1]: continue
                steps=math.ceil(((dt-hour_start).total_seconds()/60+duration)/60)
                if i+steps>len(times): continue
                values=[]; blocks=[]; reasons=[]; first_features=[]; samples=[]
                for j in range(i,i+steps):
                    if times[j]!=hour_start+timedelta(hours=j-i): blocks.append('Forecast interval is incomplete'); break
                    w={k:v[j] for k,v in h.items() if k!='time'}; features=context_features(place,ctx.get('elements',[]),w.get('wind_direction_10m'))
                    if j==i: first_features=features
                    value,b,r=score(activity,profile,w,aqmap.get(h['time'][j]),features,place,times[j],route)
                    if ctx.get('coverage_note'): r.append(ctx['coverage_note'])
                    if intent.get('sunset_only') and activity=='photography':
                        b=[reason for reason in b if reason!='Daylight required; venue lighting unverified']
                        r.append('Window uses the forecast sunset; the final part may be in low light. Check footing and the return route.')
                    if ctx.get('context_available') is False: b.append('Geographic context unavailable; road, industry, water and greenery checks could not be completed')
                    values.append(value); blocks.extend(b); reasons.extend(r); samples.append({'time':times[j].isoformat(),'weather':w,'us_aqi':aqmap.get(h['time'][j])})
                if not samples: continue
                rise=sunrises.get(dt.date().isoformat()); sunset=sunsets.get(dt.date().isoformat())
                verified_lights=place.get('tags',{}).get('lit')=='yes' and activity in ('running','tennis','football','cricket')
                if rise and sunset and not verified_lights and not (intent.get('sunset_only') and activity=='photography'):
                    if dt<local(datetime.fromisoformat(rise)) or dt+timedelta(minutes=duration)>local(datetime.fromisoformat(sunset)):
                        blocks.append('The full activity window extends outside forecast daylight; venue lighting is unverified')
                if intent.get('max_travel_minutes') and route and route['duration_minutes']>intent['max_travel_minutes']: blocks.append('Route exceeds your travel-time budget')
                missing=[]
                if intent.get('max_travel_minutes') and not commute and selected_venue is None and route is None: missing.append('Travel-time budget could not be verified because routing is unavailable')
                if ctx.get('context_available') is False: missing.append('Nearby roads, industry, water and greenery could not be checked')
                if any(sample['us_aqi'] is None for sample in samples): missing.append('Air-quality forecast is missing for part of the activity')
                if len(samples)!=steps or any(v is None for v in values): missing.append('Weather forecast is incomplete for part of the activity')
                if any(not valid_number(sample['weather'].get('wind_direction_10m'),0,360) for sample in samples): missing.append('Wind direction is missing; upwind exposure could not be checked')
                conditions=[b for b in dict.fromkeys(blocks) if not any(x in b for x in ('unavailable','incomplete','could not be completed'))]
                blocks.extend(missing)
                if not missing: complete.add(place.get('id',place['name']))
                value=None if any(v is None for v in values) else min(values)
                options.append({'place':place,'time':dt.isoformat(),'end_time':(dt+timedelta(minutes=duration)).isoformat(),'score':value,'avoid_reasons':list(dict.fromkeys(blocks)),'checks_missing':missing,'condition_reasons':conditions,'assessment':'incomplete' if missing else ('unsuitable' if conditions else 'eligible'),'tradeoffs':list(dict.fromkeys(reasons)),'weather':samples[0]['weather'],'us_aqi':samples[0]['us_aqi'],'hourly_evidence':samples,'geographic_context':first_features,'route':route,'travel_to_venue':route if not commute else None,'exercise_route':{'status':'not_verified','requested_distance_km':distance,'note':f'Conditions assessed for your {distance:g} km target and expected duration. A measured course inside this venue has not been verified; repetitions/laps are not assumed.'} if distance is not None else None,'evidence_source_ids':[s.get('id',s['url']) for s in ss],'depart_at':(dt-timedelta(minutes=route['duration_minutes'])).isoformat() if route and not commute else dt.isoformat(),'traffic_assessment':{'basis':'Mapped road proximity plus weekday commute hours; no live congestion feed','kind':'proxy'},'access_note':'Confirm venue access, opening hours and booking; map tags do not guarantee admission.'})
        except (data.SourceError,TimeoutError): failures.append('Live data unavailable or timed out for '+place['name'])
    valid=sorted([o for o in options if o['score'] is not None and not o['avoid_reasons']],key=lambda o:(-o['score'],o['place']['distance_km'],o['time']))
    best=valid[0] if valid else None; model_evidence={}
    if valid:
        shortlist=[]; seen=set()
        for o in valid:
            key=o['time'] if selected_venue else o['place'].get('id',o['place']['name'])
            if key not in seen: shortlist.append(o); seen.add(key)
            if len(shortlist)==5: break
        chosen,model_evidence=await model.choose(shortlist,activity,profile); best=shortlist[chosen]
    guidance=advice_for(activity,profile,[best] if best else options)
    alternatives=[]; seen={(best['time'] if selected_venue else best['place'].get('id',best['place']['name']))} if best else set()
    for o in valid:
        key=o['time'] if selected_venue else o['place'].get('id',o['place']['name'])
        if key not in seen: alternatives.append(o); seen.add(key)
        if len(alternatives)==3: break
    avoid=[]; seen_avoid=set()
    for o in sorted([o for o in options if o['avoid_reasons']],key=lambda o:(bool(o['checks_missing']),o['time'])):
        key=(o['place'].get('id',o['place']['name']),tuple(o['avoid_reasons']))
        if key not in seen_avoid: avoid.append(o); seen_avoid.add(key)
        if len(avoid)==5: break
    incomplete=sum(bool(o['checks_missing']) for o in options)
    unsuitable=sum(bool(o['condition_reasons']) for o in options)
    outcome={'kind':'recommendation' if best else ('mixed' if incomplete and unsuitable else 'incomplete_checks' if incomplete or not options else 'conditions_unsuitable'), 'options_with_missing_checks':incomplete,'options_with_unsuitable_conditions':unsuitable}
    return {'outcome':outcome,'status':'recommendation' if best else ('avoid_or_insufficient_data' if options else 'insufficient_data'),'request':{**intent,'duration_minutes':duration,'radius_km':None if selected_venue else radius,'search_radius_applied_km':None if selected_venue else radius},'planning_scope':'conditions_at_exact_venue' if selected_venue else 'nearby_place_comparison','search_center':{'latitude':lat,'longitude':lon},'best':best,'alternatives':alternatives,'model_reasoning_evidence':model_evidence,'summary':(f"Consider {best['place']['name']} from {best['time']} to {best['end_time']}. At the start: feels like {best['weather']['apparent_temperature']} °C, rain probability {best['weather']['precipitation_probability']}%, wind {best['weather']['wind_speed_10m']} km/h, US AQI {best['us_aqi']}." if best else ('The compared forecasts exceed prototype condition limits.' if outcome['kind']=='conditions_unsuitable' else 'Unfavourable forecast conditions and incomplete source checks prevent a recommendation.' if outcome['kind']=='mixed' else 'Required source checks could not finish; this is not a finding that the places are unsuitable.')),'avoided_options':avoid,'compared':{'venues':len(venues),'venues_with_evidence':len(complete),'venues_with_forecast':len(evaluated),'place_hour_pairs':len(options)},'advice':guidance['prepare'],'guidance':guidance,'sources':list({s.get('id',s['url']+str(s.get('parameters',{}))):s for s in sources}.values()),'data_failures':failures,'limitations':['Suitability scores and profile limits are documented prototype heuristics, not medical advice or a safety guarantee.','Air quality is a regional forecast using US AQI, not a street-level measurement.','Traffic uses mapped roads and commute-hour proxies; route times do not include live congestion.','Mapped water and greenery influence preferences and cautions; shade, barriers and local flooding are not verified. Small map extracts can omit unmapped features or enclosing polygons.','At most five compatible venues are compared. Commutes sample weather/context near a verified route midpoint, not every metre.','Opening hours, access, surface condition and booking must be checked with the venue. Exercise distance is a requested target; a measured course and lap length are not verified.'],'attribution':['© OpenStreetMap contributors','Weather: Open-Meteo','Air quality: CAMS via Open-Meteo','Geocoding: Photon / GeoNames','Routing: Valhalla / FOSSGIS'],'model':model.MODEL,'generated_at':datetime.now(TZ).isoformat()}
