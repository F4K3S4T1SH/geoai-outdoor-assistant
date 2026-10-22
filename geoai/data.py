"""Live sources with bounded queries, persisted TTL cache and request provenance."""
import asyncio
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

CACHE = Path('work/cache')
LOCK = asyncio.Lock()
COOLDOWN = {}
MAP_ENDPOINTS = ('https://overpass-api.de/api/interpreter',
                 'https://overpass.private.coffee/api/interpreter',
                 'https://maps.mail.ru/osm/tools/overpass/api/interpreter')

class SourceError(Exception):
    pass

async def fetch(url, params, ttl=900, post=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256((url+json.dumps(params, sort_keys=True)).encode()).hexdigest()
    path = CACHE / (key+'.json')
    async with LOCK:
        if path.exists():
            cached = json.loads(path.read_text(encoding='utf8'))
            if time.time()-cached['epoch'] < ttl:
                return cached['data'], dict(cached['source'], cached=True)
        try:
            timeout=httpx.Timeout(28 if post else 12, connect=4)
            async with httpx.AsyncClient(timeout=timeout, headers={'User-Agent': 'GeoAIHackathonPrototype/0.1'}) as c:
                r = await (c.post(url, data=params) if post else c.get(url, params=params))
                r.raise_for_status()
                data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            status=e.response.status_code if isinstance(e,httpx.HTTPStatusError) else type(e).__name__
            raise SourceError(f'{url}: {status}') from e
        source = {'url': str(r.request.url), 'parameters': params,
                  'fetched_at': datetime.now(timezone.utc).isoformat(), 'cached': False}
        path.write_text(json.dumps({'epoch': time.time(), 'data': data, 'source': source}), encoding='utf8')
        return data, source

async def geocode(name):
    return await fetch('https://geocoding-api.open-meteo.com/v1/search',
                       {'name': name, 'count': 5, 'language': 'en', 'format': 'json'}, ttl=86400)

async def overpass(q):
    errors=[]
    for endpoint in MAP_ENDPOINTS:
        if time.time()<COOLDOWN.get(endpoint,0):
            errors.append(endpoint+': cooling down after previous failure')
            continue
        try:
            result,source=await fetch(endpoint,{'data':q},ttl=3600,post=True)
            if result.get('remark'): raise SourceError('Map query incomplete: '+result['remark'])
            return result,source
        except SourceError as e:
            COOLDOWN[endpoint]=time.time()+30
            errors.append(str(e))
    raise SourceError('; '.join(errors))

def distance(a, b):
    p1,p2 = math.radians(a[0]),math.radians(b[0])
    dp,dl = p2-p1,math.radians(b[1]-a[1])
    return 6371*2*math.asin(min(1,math.sqrt(math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2)))

def bearing(a,b):
    p1,p2=map(math.radians,[a[0],b[0]])
    dl=math.radians(b[1]-a[1])
    return math.degrees(math.atan2(math.sin(dl)*math.cos(p2), math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)))%360

async def places(lat,lon,radius):
    q = f'''[out:json][timeout:25];(nwr(around:{int(radius*1000)},{lat},{lon})[leisure~"^(park|pitch|sports_centre|golf_course|nature_reserve|garden)$"];nwr(around:{int(radius*1000)},{lat},{lon})[tourism="viewpoint"];);out center tags;'''
    data, source = await overpass(q)
    found=[]
    for e in data.get('elements',[]):
        t=e.get('tags',{}); p=e.get('center',e)
        if not t.get('name') or t.get('access') in ('private','no') or 'lat' not in p:
            continue
        d=distance((lat,lon),(p['lat'],p['lon']))
        if d <= radius:
            found.append({'id':f"{e['type']}/{e['id']}", 'name':t['name'], 'lat':p['lat'], 'lon':p['lon'],
                          'distance_km':round(d,2), 'tags':t, 'url':f"https://www.openstreetmap.org/{e['type']}/{e['id']}"})
    return sorted(found,key=lambda v:v['distance_km']),source

async def context(lat,lon):
    q=f'''[out:json][timeout:20];(way(around:700,{lat},{lon})[highway~"^(motorway|trunk|primary)$"];nwr(around:1000,{lat},{lon})[landuse="industrial"];nwr(around:500,{lat},{lon})[natural="water"];nwr(around:500,{lat},{lon})[landuse~"^(forest|grass)$"];);out center tags geom;'''
    return await overpass(q)

async def forecast(lat,lon):
    return await fetch('https://api.open-meteo.com/v1/forecast', {'latitude':lat,'longitude':lon,
        'hourly':'temperature_2m,apparent_temperature,precipitation_probability,wind_speed_10m,wind_direction_10m,weather_code,is_day,uv_index',
        'timezone':'Asia/Kolkata','forecast_days':7})

async def air(lat,lon):
    return await fetch('https://air-quality-api.open-meteo.com/v1/air-quality',
        {'latitude':lat,'longitude':lon,'hourly':'us_aqi,pm2_5','timezone':'Asia/Kolkata','forecast_days':5})
