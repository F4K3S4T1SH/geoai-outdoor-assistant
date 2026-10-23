"""Transparent prototype heuristics, not medical or pollution dispersion models."""
import math
from .data import distance, bearing

ACTIVITIES = {
 'running': (32,25,45), 'cycling':(33,25,50), 'golf':(34,20,35),
 'cricket':(33,25,40), 'football':(32,25,40), 'tennis':(32,18,35),
 'hiking':(30,25,40), 'picnic':(34,25,35), 'event':(34,20,30), 'photography':(35,30,45)}
SPORTS={'golf':'golf','cricket':'cricket','football':'soccer','tennis':'tennis'}

def suitable(place,activity):
    tags=place['tags']; leisure=tags.get('leisure'); sport=tags.get('sport','').split(';')
    if tags.get('indoor')=='yes' or tags.get('covered')=='yes': return False
    if activity=='golf': return leisure=='golf_course' or 'golf' in sport
    if activity in SPORTS: return SPORTS[activity] in sport or tags.get('inferred_sport')==SPORTS[activity]
    if activity=='cycling': return (leisure in ('park','nature_reserve') or tags.get('highway')=='cycleway' or tags.get('bicycle')=='designated') and tags.get('bicycle')!='no'
    if activity=='hiking': return leisure in ('park','garden','nature_reserve') or tags.get('highway') in ('path','trailhead')
    if activity in ('picnic','event'): return leisure in ('park','garden') or tags.get('tourism')=='picnic_site'
    return leisure in ('park','garden','nature_reserve') or (activity=='photography' and tags.get('tourism')=='viewpoint')

def context_features(place,elements,wind):
    out=[]; here=(place['lat'],place['lon'])
    for e in elements:
        tags=e.get('tags',{}); p=e.get('center',e)
        points=[(g['lat'],g['lon']) for g in e.get('geometry',[]) if 'lat' in g]
        if not points and 'lat' in p: points=[(p['lat'],p['lon'])]
        if not points: continue
        nearest=min(points,key=lambda p:distance(here,p)); d=distance(here,nearest)
        kind='major_road' if 'highway' in tags else ('industry' if tags.get('landuse')=='industrial' else ('water' if tags.get('natural')=='water' else 'green_cover'))
        delta=abs((bearing(here,nearest)-wind+180)%360-180) if wind is not None else None
        out.append({'kind':kind,'distance_m':round(d*1000),'upwind_sector': delta is not None and delta<=45,
                    'road_class':tags.get('highway'),'mapped_lanes':tags.get('lanes'),'mapped_maxspeed':tags.get('maxspeed'),
                    'osm_id':f"{e['type']}/{e['id']}"})
    return out

def score(activity,profile,w,aq,features,place=None,when=None,route=None):
    heat,rain,wind=ACTIVITIES[activity]
    sensitive=profile!='general'
    if sensitive: heat-=3
    blockers=[]; reasons=[]; penalty=0
    if place and place.get('tags',{}).get('inferred_sport'): reasons.append('Activity inferred from the mapped place name; verify facilities directly')
    required=['apparent_temperature','precipitation_probability','wind_speed_10m','weather_code','is_day']
    if any(w.get(k) is None for k in required): return None,['Weather data incomplete'],[]
    if w['weather_code'] in (95,96,99): blockers.append('Thunderstorm forecast')
    if w['apparent_temperature']>heat: blockers.append('Apparent temperature exceeds prototype activity limit')
    if w['apparent_temperature']<5: blockers.append('Cold conditions exceed prototype limit')
    if w['wind_speed_10m']>wind: blockers.append('Wind exceeds prototype activity limit')
    if w['precipitation_probability']>=rain: penalty+=25; reasons.append('Elevated rain probability')
    if w['precipitation_probability']>=75: blockers.append('High rain probability exceeds prototype activity limit')
    lit=place is not None and place.get('tags',{}).get('lit')=='yes' and activity in ('tennis','football','cricket','running')
    if not w['is_day'] and not lit: blockers.append('Daylight required; venue lighting unverified')
    if aq is None: blockers.append('Air-quality forecast unavailable; cannot assess suitability')
    elif aq > (50 if sensitive else 100): blockers.append('US AQI exceeds prototype profile limit')
    elif aq>50: penalty+=10; reasons.append('Air quality below good range (US AQI)')
    if (w.get('uv_index') or 0)>=6: penalty+=10; reasons.append('High forecast UV index')
    upwind=[f for f in features if f['kind'] in ('major_road','industry') and f['upwind_sector'] and f['distance_m']<700]
    if upwind: penalty+=15; reasons.append('Mapped road or industry lies in the upwind sector; exposure proxy only')
    roads=[f for f in features if f['kind']=='major_road' and f['distance_m']<250]
    if roads:
        penalty+=5; reasons.append('Mapped major road within 250 m; traffic exposure proxy')
        if when and when.weekday()<5 and (7<=when.hour<10 or 17<=when.hour<20):
            penalty+=8; reasons.append('Weekday commute-hour traffic proxy; live traffic volumes are unavailable')
    green=[f for f in features if f['kind']=='green_cover' and f['distance_m']<=300]
    if green:
        penalty-=3; reasons.append('Mapped greenery within 300 m; small preference bonus, shade is not verified')
    water=[f for f in features if f['kind']=='water' and f['distance_m']<=200]
    if water:
        if profile=='child' or activity in ('picnic','event','hiking'):
            penalty+=5; reasons.append('Water within 200 m: check edge barriers, supervision and footing')
        if w['precipitation_probability']>=30 or w['wind_speed_10m']>=25:
            penalty+=8; reasons.append('Nearby water combined with rain or wind: extra edge and footing caution')
    if route:
        penalty+=min(15,route['duration_minutes']/10)
    penalty+=max(0,w['apparent_temperature']-24)*1.2
    return round(min(100,max(0,100-penalty)),1),blockers,reasons
