"""Transparent prototype heuristics, not medical or pollution dispersion models."""
import math
from .data import distance, bearing

ACTIVITIES = {
 'running': (32,25,45), 'cycling':(33,25,50), 'golf':(34,20,35),
 'cricket':(33,25,40), 'football':(32,25,40), 'tennis':(32,18,35),
 'hiking':(30,25,40), 'picnic':(34,25,35), 'event':(34,20,30), 'photography':(35,30,45)}
SPORTS={'golf':'golf','cricket':'cricket','football':'soccer','tennis':'tennis'}

def valid_number(value,low=-math.inf,high=math.inf):
    return type(value) in (int,float) and math.isfinite(value) and low<=value<=high

def nearest_on_geometry(here,points):
    """Project onto segments, rather than measuring only distant road vertices."""
    if len(points)<2: return points[0]
    scale=math.cos(math.radians(here[0])); candidates=list(points)
    for a,b in zip(points,points[1:]):
        ax=(a[1]-here[1])*scale; ay=a[0]-here[0]
        dx=(b[1]-a[1])*scale; dy=b[0]-a[0]; norm=dx*dx+dy*dy
        t=max(0,min(1,-(ax*dx+ay*dy)/norm)) if norm else 0
        candidates.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
    return min(candidates,key=lambda p:distance(here,p))

def inside_ring(here,points):
    if len(points)<4 or points[0]!=points[-1]: return False
    y,x=here; inside=False
    for (ay,ax),(by,bx) in zip(points,points[1:]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax: inside=not inside
    return inside

def suitable(place,activity):
    tags=place['tags']; leisure=tags.get('leisure'); sport=tags.get('sport','').split(';')
    if tags.get('indoor')=='yes' or tags.get('covered')=='yes' or tags.get('access') in ('private','no'): return False
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
        nearest=nearest_on_geometry(here,points); d=distance(here,nearest)
        if tags.get('highway') in ('motorway','trunk','primary'): kind='major_road'
        elif tags.get('landuse')=='industrial': kind='industry'
        elif tags.get('natural')=='water': kind='water'
        elif tags.get('landuse') in ('forest','grass') or tags.get('natural')=='wood' or tags.get('leisure') in ('park','garden'): kind='green_cover'
        else: continue
        within=kind in ('green_cover','industry','water') and inside_ring(here,points)
        if within: d=0
        delta=abs((bearing(here,nearest)-wind+180)%360-180) if wind is not None else None
        out.append({'kind':kind,'distance_m':round(d*1000),'inside_mapped_area':within,'upwind_sector': not within and delta is not None and delta<=45,
                    'road_class':tags.get('highway'),'mapped_lanes':tags.get('lanes'),'mapped_maxspeed':tags.get('maxspeed'),
                    'osm_id':f"{e['type']}/{e['id']}"})
    return out

def score(activity,profile,w,aq,features,place=None,when=None,route=None):
    heat,rain,wind=ACTIVITIES[activity]
    sensitive=profile!='general'
    if sensitive: heat-=3
    blockers=[]; reasons=[]; penalty=0
    if place and place.get('map_note'): reasons.append(place['map_note'])
    if place and place.get('tags',{}).get('inferred_sport'): reasons.append('Activity inferred from the mapped place name; verify facilities directly')
    required=['apparent_temperature','precipitation_probability','wind_speed_10m','weather_code','is_day']
    if any(not valid_number(w.get(k)) for k in required): return None,['Weather data incomplete or invalid'],[]
    if not valid_number(w['precipitation_probability'],0,100) or not valid_number(w['wind_speed_10m'],0,500) or w['is_day'] not in (0,1): return None,['Weather data incomplete or invalid'],[]
    if w['weather_code'] not in {0,1,2,3,45,48,51,53,55,56,57,61,63,65,66,67,71,73,75,77,80,81,82,85,86,95,96,99}: return None,['Weather data incomplete or invalid'],[]
    if w['weather_code'] in (95,96,99): blockers.append('Thunderstorm forecast')
    if w['apparent_temperature']>heat: blockers.append('Apparent temperature exceeds prototype activity limit')
    if w['apparent_temperature']<5: blockers.append('Cold conditions exceed prototype limit')
    if w['wind_speed_10m']>wind: blockers.append('Wind exceeds prototype activity limit')
    if w['precipitation_probability']>=rain: penalty+=25; reasons.append('Elevated rain probability')
    if w['precipitation_probability']>=75: blockers.append('High rain probability exceeds prototype activity limit')
    lit=place is not None and place.get('tags',{}).get('lit')=='yes' and activity in ('tennis','football','cricket','running')
    if not w['is_day'] and not lit: blockers.append('Daylight required; venue lighting unverified')
    if not valid_number(aq,0,500): blockers.append('Air-quality forecast unavailable or invalid; cannot assess suitability')
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
    if any(f['kind']=='industry' and f['distance_m']<250 for f in features):
        penalty+=10; reasons.append('Mapped industrial land use within 250 m; proximity proxy, not measured emissions')
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
