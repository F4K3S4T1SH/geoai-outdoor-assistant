from datetime import datetime,timedelta
import pytest
from fastapi.testclient import TestClient
from geoai import app as module
from geoai.intent import normalize

NOW=datetime(2026,10,23,8,tzinfo=module.TZ)

@pytest.mark.parametrize('question,distance,radius,scope',[
    ('10 kms Run in Bharathi Park, puducherry',10,10,'exact'),
    ('Run 5 km near Cubbon Park within 2 km',5,2,'nearby'),
    ('Run within 5 km of Cubbon Park',None,5,'nearby'),
    ('Run a 10-km distance inside Bharathi Park tomorrow',10,10,'exact'),
    ('Walk 3 kilometres at Bharathi Park tomorrow',3,10,'exact'),
    ('Find a picnic within 5 km of Powai',None,5,'nearby'),
    ('Run in the morning near Cubbon Park',None,10,'nearby'),
    ('Run in a park near Powai',None,10,'nearby'),
])
def test_exercise_distance_and_venue_scope_are_independent(question,distance,radius,scope):
    parsed=normalize({'activity':'running','radius_km':99},question,NOW)
    assert parsed['exercise_distance_km']==distance
    assert parsed['radius_km']==radius
    assert parsed['venue_scope']==scope

def test_pace_is_not_mistaken_for_activity_duration():
    parsed=normalize({'activity':'running'},'10 km run in Bharathi Park tomorrow at 6 min/km',NOW)
    assert parsed['pace_minutes_per_km']==6
    assert parsed['duration_explicit'] is False

def test_distance_and_pace_define_the_single_clock_window():
    parsed=normalize({'activity':'running'},'20 km run in Bharathi Park tomorrow at 8 am at 6 min/km',NOW)
    assert parsed['duration_minutes']==120
    assert parsed['end']=='2026-10-24T10:00'

def test_short_run_duration_is_not_silently_inflated():
    parsed=normalize({'activity':'running'},'1 km run in Bharathi Park for 5 minutes tomorrow',NOW)
    assert parsed['duration_minutes']==5

def test_distance_requires_duration_without_network_substitution(monkeypatch):
    async def extract(*_): return {'activity':'running','profile':'general'}
    async def must_not_fetch(*_): raise AssertionError('Ask for duration before searching other venues')
    monkeypatch.setattr(module.model,'extract',extract)
    monkeypatch.setattr(module.data,'places',must_not_fetch)
    result=TestClient(module.app).post('/ask',json={'question':'10 kms Run in Bharathi Park, puducherry'}).json()
    assert result['status']=='clarification_needed'
    assert result['field']=='duration'
    assert result['parsed_request']['exercise_distance_km']==10
    assert result['parsed_request']['requested_venue']=='Bharathi Park, puducherry'

@pytest.fixture
def scoped_sources(monkeypatch):
    t=(datetime.now(module.TZ)+timedelta(days=1)).replace(hour=8,minute=0,second=0,microsecond=0)
    source={'url':'synthetic fixture, not live data'}
    park={'id':'node/123','name':'Bharathi Park','lat':11.9336,'lon':79.8347,'distance_km':0,'tags':{'leisure':'park'},'url':'https://www.openstreetmap.org/node/123'}
    calls={'places':0,'route':0,'choices':0}
    async def extract(*_): return {'activity':'running','profile':'general','location':'wrong model location','radius_km':10}
    async def venue(identity):
        assert identity=='node/123'
        return park,source
    async def weather(*_): return {'hourly':{'time':[(t+timedelta(hours=i)).replace(tzinfo=None).isoformat(timespec='minutes') for i in range(4)],'apparent_temperature':[25]*4,'temperature_2m':[24]*4,'precipitation_probability':[0]*4,'wind_speed_10m':[5]*4,'wind_direction_10m':[0]*4,'weather_code':[0]*4,'is_day':[1]*4,'uv_index':[2]*4}},source
    async def air(*_): return {'hourly':{'time':[(t+timedelta(hours=i)).replace(tzinfo=None).isoformat(timespec='minutes') for i in range(4)],'us_aqi':[30]*4}},source
    async def context(*_): return {'elements':[]},source
    async def places(*_): calls['places']+=1; return [park],source
    async def route(*_):
        calls['route']+=1
        return {'mode':'pedestrian','duration_minutes':40,'distance_km':3,'geometry':{'type':'LineString','coordinates':[]}},source
    async def choose(options,*_): calls['choices']=len(options); return 0,{}
    monkeypatch.setattr(module.model,'extract',extract); monkeypatch.setattr(module.model,'choose',choose)
    for name,fn in [('venue',venue),('forecast',weather),('air',air),('context',context),('places',places),('route',route)]: monkeypatch.setattr(module.data,name,fn)
    return t,calls

@pytest.mark.parametrize('timing',[{'pace_minutes_per_km':6},{'duration_minutes':50}])
def test_exact_venue_is_preserved_and_distance_course_is_not_invented(scoped_sources,timing):
    t,calls=scoped_sources
    result=TestClient(module.app).post('/ask',json={'question':'10 kms Run in Bharathi Park, puducherry','venue_id':'node/123','start':t.isoformat(),'end':(t+timedelta(hours=4)).isoformat(),**timing}).json()
    assert result['status']=='recommendation',result
    assert result['planning_scope']=='conditions_at_exact_venue'
    assert result['request']['exercise_distance_km']==10
    assert result['request']['duration_minutes']==(60 if 'pace_minutes_per_km' in timing else 50)
    assert result['request']['search_radius_applied_km'] is None
    assert result['compared']['venues']==1
    assert calls['places']==calls['route']==0
    assert calls['choices']>1  # Compare times at the same venue, not new parks.
    options=[result['best'],*result['alternatives']]
    assert len(options)==4
    assert len({o['time'] for o in options})==4
    assert {o['place']['id'] for o in options}=={'node/123'}
    assert all(o['route'] is None and o['travel_to_venue'] is None for o in options)
    assert all(o['exercise_route']['status']=='not_verified' for o in options)

def test_nearby_search_labels_transport_without_changing_exercise_duration(scoped_sources):
    t,calls=scoped_sources
    result=TestClient(module.app).post('/ask',json={'question':'Run near Bharathi Park','latitude':11.93,'longitude':79.83,'start':t.isoformat(),'end':(t+timedelta(hours=4)).isoformat()}).json()
    assert result['status']=='recommendation',result
    assert calls['places']==calls['route']==1
    assert result['request']['duration_minutes']==60
    assert result['best']['route']['purpose']=='travel_to_venue'
    assert result['best']['travel_to_venue']['duration_minutes']==40
    assert result['best']['exercise_route'] is None

def test_invalid_venue_identity_cannot_be_used_as_a_url():
    response=TestClient(module.app).post('/ask',json={'question':'Run in a park','venue_id':'https://example.com/private'})
    assert response.status_code==422

def test_exact_venue_outage_does_not_substitute_another_park(scoped_sources,monkeypatch):
    t,calls=scoped_sources
    async def outage(*_): raise module.data.SourceError('Fixture outage')
    monkeypatch.setattr(module.data,'venue',outage)
    result=TestClient(module.app).post('/ask',json={'question':'Run in Bharathi Park','venue_id':'node/123','start':t.isoformat(),'end':(t+timedelta(hours=2)).isoformat()}).json()
    assert result['status']=='insufficient_data'
    assert calls['places']==calls['route']==0
    assert 'no other park was substituted' in result['message']

def test_commute_does_not_silently_replace_an_exercise_distance(scoped_sources):
    result=TestClient(module.app).post('/ask',json={'question':'10 km cycling commute tomorrow','activity':'cycling','mode':'commute','exercise_distance_km':10,'pace_minutes_per_km':3}).json()
    assert result['status']=='clarification_needed'
    assert 'leisure ride' in result['question']


def test_confirmed_identity_is_verified_from_map_data(monkeypatch):
    import asyncio
    from geoai import data
    async def fetch(url,params,**kwargs):
        assert url=='https://api.openstreetmap.org/api/0.6/way/123/full.json'
        return {'elements':[{'type':'node','id':1,'lat':11,'lon':79},{'type':'node','id':2,'lat':11.01,'lon':79.01},{'type':'way','id':123,'nodes':[1,2],'tags':{'name':'Mapped park','leisure':'park'}}]},{'url':url}
    monkeypatch.setattr(data,'fetch',fetch)
    park,source=asyncio.run(data.venue('way/123'))
    assert park['id']=='way/123'
    assert park['name']=='Mapped park'
    assert park['lat']==pytest.approx(11.005)
