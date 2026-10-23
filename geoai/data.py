"""Live sources with bounded queries, persisted TTL cache and request provenance."""
import asyncio
import hashlib
import json
import math
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import httpx

CACHE = Path('work/cache')
LOCK = asyncio.Lock()
SOURCE_LOCKS=defaultdict(asyncio.Lock)
LAST_CALL={}
COOLDOWN = {}
MAP_ENDPOINTS = ('https://overpass-api.de/api/interpreter',
                 'https://overpass.private.coffee/api/interpreter',
                 'https://maps.mail.ru/osm/tools/overpass/api/interpreter')

class SourceError(Exception):
    pass

def cache_path(url,params):
    return CACHE / (hashlib.sha256((url+json.dumps(params,sort_keys=True)).encode()).hexdigest()+'.json')

def read_cache(url,params,ttl):
    try:
        cached=json.loads(cache_path(url,params).read_text(encoding='utf8'))
        if time.time()-cached['epoch']<ttl and not cached['data'].get('remark'):
            return cached['data'],dict(cached['source'],cached=True)
    except (OSError,ValueError,KeyError,AttributeError): pass
    return None

def parse_osm_context(xml):
    """Keep map evidence only, reconstructing ways from the supplied nodes."""
    root=ET.fromstring(xml)
    if root.tag!='osm': raise ValueError('Not an OSM map response')
    nodes={e.attrib['id']:{'lat':float(e.attrib['lat']),'lon':float(e.attrib['lon'])} for e in root.findall('node')}
    ways={e.attrib['id']:[nodes[n.attrib['ref']] for n in e.findall('nd') if n.attrib['ref'] in nodes] for e in root.findall('way')}
    elements=[]
    for e in root:
        tags={t.attrib['k']:t.attrib['v'] for t in e.findall('tag')}
        if not (tags.get('highway') in ('motorway','trunk','primary') or tags.get('landuse') in ('industrial','forest','grass') or tags.get('natural') in ('water','wood') or tags.get('leisure') in ('park','garden','pitch','sports_centre','golf_course','nature_reserve') or tags.get('tourism') in ('viewpoint','picnic_site') or tags.get('highway') in ('cycleway','path','trailhead')): continue
        geometry=([nodes[e.attrib['id']]] if e.tag=='node' else ways.get(e.attrib['id'],[]))
        if e.tag=='relation': geometry=[p for m in e.findall('member') if m.attrib.get('type')=='way' for p in ways.get(m.attrib['ref'],[])]
        if not geometry: continue
        elements.append({'type':e.tag,'id':int(e.attrib['id']),'tags':tags,'geometry':geometry,'center':{'lat':sum(p['lat'] for p in geometry)/len(geometry),'lon':sum(p['lon'] for p in geometry)/len(geometry)}})
    return {'elements':elements,'context_available':True,'coverage_note':'Small OSM map extract; unmapped features and polygons without nodes in the extract may be absent.'}

async def fetch(url, params, ttl=900, post=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256((url+json.dumps(params, sort_keys=True)).encode()).hexdigest()
    path = CACHE / (key+'.json')
    async with SOURCE_LOCKS[url]:
        cached=read_cache(url,params,ttl)
        if cached: return cached
        try:
            if any(s in url for s in ('overpass','photon','valhalla','api.openstreetmap.org')):
                delay=1.1-(time.monotonic()-LAST_CALL.get(url,0))
                if delay>0: await asyncio.sleep(delay)
                LAST_CALL[url]=time.monotonic()
            timeout=httpx.Timeout(28 if post else 12, connect=4)
            async with httpx.AsyncClient(timeout=timeout, headers={'User-Agent': 'GeoAIHackathonPrototype/0.2'}) as c:
                r = await (c.post(url, data=params) if post else c.get(url, params=params))
                r.raise_for_status()
                data = parse_osm_context(r.text) if url=='https://api.openstreetmap.org/api/0.6/map' else r.json()
                if isinstance(data,dict) and data.get('remark'): raise SourceError('Map service returned incomplete data')
        except (httpx.HTTPError, ValueError,ET.ParseError) as e:
            status=e.response.status_code if isinstance(e,httpx.HTTPStatusError) else type(e).__name__
            raise SourceError(f'{url}: {status}') from e
        source = {'id':key[:12],'url': str(r.request.url), 'parameters': params,
                  'fetched_at': datetime.now(timezone.utc).isoformat(), 'cached': False}
        path.write_text(json.dumps({'epoch': time.time(), 'data': data, 'source': source}), encoding='utf8')
        return data, source

async def geocode(name):
    try:
        raw,source=await fetch('https://photon.komoot.io/api/',{'q':name,'limit':5},ttl=86400)
        hits=[]
        for feature in raw.get('features',[]):
            p=feature.get('properties',{}); coords=feature.get('geometry',{}).get('coordinates',[])
            if len(coords)!=2: continue
            hits.append({'name':p.get('name',name),'latitude':coords[1],'longitude':coords[0],
                'admin1':p.get('state',''),'admin2':p.get('city',''),'country':p.get('country',''),
                'label':', '.join(dict.fromkeys(x for x in (p.get('name'),p.get('city'),p.get('state'),p.get('country')) if x))})
        if hits: return {'results':hits},source
    except SourceError: pass
    return await fetch('https://geocoding-api.open-meteo.com/v1/search',
                       {'name': name, 'count': 5, 'language': 'en', 'format': 'json'}, ttl=86400)

async def overpass(q,budget=6):
    errors=[]
    # A server outage must never hide fresh evidence already in our cache.
    for endpoint in MAP_ENDPOINTS:
        cached=read_cache(endpoint,{'data':q},86400)
        if cached: return cached
    for endpoint in MAP_ENDPOINTS:
        if time.time()<COOLDOWN.get(endpoint,0):
            errors.append(endpoint+': cooling down after previous failure')
            continue
        try:
            result,source=await asyncio.wait_for(fetch(endpoint,{'data':q},ttl=86400,post=True),timeout=budget)
            if result.get('remark'): raise SourceError('Map query incomplete: '+result['remark'])
            return result,source
        except (SourceError,TimeoutError) as e:
            COOLDOWN[endpoint]=time.time()+30
            errors.append(str(e) or endpoint+': request budget exceeded')
    raise SourceError('; '.join(errors))

def distance(a, b):
    p1,p2 = math.radians(a[0]),math.radians(b[0])
    dp,dl = p2-p1,math.radians(b[1]-a[1])
    return 6371*2*math.asin(min(1,math.sqrt(math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2)))

def bearing(a,b):
    p1,p2=map(math.radians,[a[0],b[0]])
    dl=math.radians(b[1]-a[1])
    return math.degrees(math.atan2(math.sin(dl)*math.cos(p2), math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)))%360

async def places(lat,lon,radius,activity=None):
    trails=f'nwr(around:{int(radius*1000)},{lat},{lon})[highway~"^(cycleway|path|trailhead)$"];' if activity in ('hiking','cycling') else ''
    q = f'''[out:json][timeout:25];(nwr(around:{int(radius*1000)},{lat},{lon})[leisure~"^(park|pitch|sports_centre|golf_course|nature_reserve|garden)$"];nwr(around:{int(radius*1000)},{lat},{lon})[tourism="viewpoint"];{trails});out center tags;'''
    try: data, source = await overpass(q)
    except SourceError:
        from .ranking import suitable
        try:
            fallback,source=await photon_places(lat,lon,radius,activity)
            if any(suitable(p,activity or 'picnic') for p in fallback): return fallback,source
        except SourceError: pass
        data,source=await map_extract(lat,lon)
        source['coverage_note']='Venue fallback checked a small map extract about 1 km around the search centre, not the entire requested radius.'
    found=[]
    for e in data.get('elements',[]):
        t=e.get('tags',{}); p=e.get('center',e)
        geometry=e.get('geometry',[])
        if 'lat' not in p and geometry:
            p={'lat':sum(g['lat'] for g in geometry)/len(geometry),'lon':sum(g['lon'] for g in geometry)/len(geometry)}
        if t.get('access') in ('private','no') or t.get('indoor')=='yes' or t.get('covered')=='yes' or 'lat' not in p:
            continue
        name=t.get('name') or t.get('ref')
        if not name:
            if t.get('highway') not in ('cycleway','path','trailhead'): continue
            name=f"Mapped {t['highway']} (OSM {e['id']})"
        d=distance((lat,lon),(p['lat'],p['lon']))
        if d <= radius:
            if any(distance((v['lat'],v['lon']),(p['lat'],p['lon']))<0.12 and v['name'].lower().rstrip('s')==name.lower().rstrip('s') for v in found): continue
            found.append({'id':f"{e['type']}/{e['id']}", 'name':name, 'lat':p['lat'], 'lon':p['lon'],
                          'distance_km':round(d,2), 'tags':t, 'url':f"https://www.openstreetmap.org/{e['type']}/{e['id']}"})
    if source.get('coverage_note'):
        for place in found: place['map_note']=source['coverage_note']
    return sorted(found,key=lambda v:v['distance_km']),source

async def photon_places(lat,lon,radius,activity):
    """Live OSM place-search fallback; never fills in missing map features."""
    term={'golf':'golf','cricket':'cricket','football':'football','tennis':'tennis','photography':'viewpoint','cycling':'park'}.get(activity,'park')
    dy=radius/111; dx=radius/(111*max(.1,math.cos(math.radians(lat))))
    raw,source=await fetch('https://photon.komoot.io/api/',{'q':term,'lat':lat,'lon':lon,'limit':30,'bbox':f'{lon-dx},{lat-dy},{lon+dx},{lat+dy}'},ttl=3600)
    found=[]
    for feature in raw.get('features',[]):
        p=feature.get('properties',{}); coords=feature.get('geometry',{}).get('coordinates',[])
        if len(coords)!=2 or not p.get('name'): continue
        tags={p.get('osm_key','unknown'):p.get('osm_value','unknown')}
        if p.get('osm_key') not in ('leisure','tourism','highway','sport'): continue
        d=distance((lat,lon),(coords[1],coords[0]))
        if d>radius: continue
        osmtype={'N':'node','W':'way','R':'relation'}.get(p.get('osm_type'),p.get('osm_type','node'))
        if activity in ('cricket','football','tennis') and term in p['name'].lower(): tags['inferred_sport']={'football':'soccer'}.get(activity,activity)
        found.append({'id':f"{osmtype}/{p['osm_id']}",'name':p['name'],'lat':coords[1],'lon':coords[0],
            'distance_km':round(d,2),'tags':tags,'url':f"https://www.openstreetmap.org/{osmtype}/{p['osm_id']}",
            'map_note':'Photon fallback supplies limited map tags; venue access and facilities remain unverified.'})
    source['note']='Live Photon / OpenStreetMap fallback after Overpass outage; limited venue metadata'
    return sorted(found,key=lambda p:p['distance_km']),source

def extract_bbox(lat,lon):
    dy=1.05/111; dx=dy/max(.1,math.cos(math.radians(lat)))
    return f'{max(-180,lon-dx):.6f},{max(-90,lat-dy):.6f},{min(180,lon+dx):.6f},{min(90,lat+dy):.6f}'

async def map_extract(lat,lon):
    result,source=await asyncio.wait_for(fetch('https://api.openstreetmap.org/api/0.6/map',{'bbox':extract_bbox(lat,lon)},ttl=86400),timeout=8)
    source['note']='Small OSM map extract fallback after map-search outage; map coverage is not a guarantee of feature absence.'
    return result,source

async def context(lat,lon):
    cached=read_cache('https://api.openstreetmap.org/api/0.6/map',{'bbox':extract_bbox(lat,lon)},86400)
    if cached: return cached
    q=f'''[out:json][timeout:20];(way(around:700,{lat},{lon})[highway~"^(motorway|trunk|primary)$"];nwr(around:1000,{lat},{lon})[landuse="industrial"];nwr(around:500,{lat},{lon})[natural="water"];nwr(around:500,{lat},{lon})[landuse~"^(forest|grass)$"];);out center tags geom;'''
    try:
        return await asyncio.wait_for(overpass(q,budget=2.7),timeout=4)
    except (SourceError,TimeoutError):
        # Bounded read-only extracts, serialized and cached; never bulk downloads.
        return await map_extract(lat,lon)

async def forecast(lat,lon):
    return await fetch('https://api.open-meteo.com/v1/forecast', {'latitude':lat,'longitude':lon,
        'hourly':'temperature_2m,apparent_temperature,precipitation_probability,wind_speed_10m,wind_direction_10m,weather_code,is_day,uv_index',
        'daily':'sunrise,sunset','timezone':'Asia/Kolkata','forecast_days':7})

async def air(lat,lon):
    return await fetch('https://air-quality-api.open-meteo.com/v1/air-quality',
        {'latitude':lat,'longitude':lon,'hourly':'us_aqi,pm2_5','timezone':'Asia/Kolkata','forecast_days':5})

def decode_shape(encoded):
    if isinstance(encoded,dict): return encoded.get('coordinates',[])
    coords=[]; index=0; lat=lon=0
    while index<len(encoded):
        values=[]
        for _ in range(2):
            value=shift=0
            while True:
                b=ord(encoded[index])-63; index+=1; value|=(b&31)<<shift; shift+=5
                if b<32: break
            values.append(~(value>>1) if value&1 else value>>1)
        lat+=values[0]; lon+=values[1]; coords.append([lon/1e6,lat/1e6])
    return coords

async def route(origin,destination,mode='pedestrian'):
    payload={'locations':[{'lat':origin[0],'lon':origin[1]},{'lat':destination[0],'lon':destination[1]}],
             'costing':mode,'units':'kilometers','directions_options':{'units':'kilometers'}}
    raw,source=await fetch('https://valhalla1.openstreetmap.de/route',{'json':json.dumps(payload,separators=(',',':'))},ttl=3600)
    trip=raw.get('trip',{})
    if trip.get('status')!=0 or not trip.get('legs'): raise SourceError('Routing service could not verify a route')
    shape=[]
    for leg in trip['legs']: shape.extend(decode_shape(leg.get('shape','')))
    return {'distance_km':round(trip['summary']['length'],2),'duration_minutes':round(trip['summary']['time']/60,1),
            'mode':mode,'geometry':{'type':'LineString','coordinates':shape},
            'traffic_basis':'OSM road-network estimate; no live congestion feed'},source
