import asyncio
from datetime import datetime,timedelta
from fastapi.testclient import TestClient
from geoai import app as module
from geoai.data import SourceError

def test_model_health_is_honest():
    response=TestClient(module.app).get('/activities')
    assert len(response.json())==10

def test_missing_location_asks_instead_of_inventing(monkeypatch):
    async def extract(*args): return {'activity':'running','location':None}
    monkeypatch.setattr(module.model,'extract',extract)
    r=TestClient(module.app).post('/ask',json={'question':'Go running tomorrow?'})
    assert r.status_code==200
    assert r.json()['status']=='clarification_needed'

def test_live_source_failure_is_not_fabricated(monkeypatch):
    now=datetime.now(module.TZ)
    async def extract(*args):
        return {'activity':'running','start':(now+timedelta(hours=1)).isoformat(),
                'end':(now+timedelta(hours=4)).isoformat(),'radius_km':5}
    async def fail(*args): raise SourceError('Map provider unavailable')
    monkeypatch.setattr(module.model,'extract',extract)
    monkeypatch.setattr(module.data,'places',fail)
    r=TestClient(module.app).post('/ask',json={'question':'Compare running conditions','latitude':19,'longitude':73})
    assert r.status_code==503
    assert r.json()['detail']['status']=='source_unavailable'

def test_grounded_recommendation_flow(monkeypatch):
    now=datetime.now(module.TZ)
    t=(now+timedelta(hours=2)).replace(minute=0,second=0,microsecond=0)
    source={'url':'test fixture, not live data'}
    async def extract(*args): return {'activity':'running','profile':'general','radius_km':5,'start':(t-timedelta(hours=1)).isoformat(),'end':(t+timedelta(hours=1)).isoformat()}
    async def places(*args): return [{'name':'Fixture park','lat':19,'lon':73,'tags':{'leisure':'park'},'distance_km':1}],source
    async def forecast(*args): return {'hourly':{'time':[t.replace(tzinfo=None).isoformat(timespec='minutes')], 'apparent_temperature':[25],'temperature_2m':[24],'precipitation_probability':[0],'wind_speed_10m':[5],'wind_direction_10m':[0],'weather_code':[0],'is_day':[1],'uv_index':[2]}},source
    async def air(*args): return {'hourly':{'time':[t.replace(tzinfo=None).isoformat(timespec='minutes')],'us_aqi':[30]}},source
    async def context(*args): return {'elements':[]},source
    async def route(*args): raise SourceError('Routing unavailable in this fixture')
    monkeypatch.setattr(module.data,'route',route)
    for name,fn in [('places',places),('forecast',forecast),('air',air),('context',context)]: monkeypatch.setattr(module.data,name,fn)
    monkeypatch.setattr(module.model,'extract',extract)
    async def choose(*args): return 0,{'us_aqi':30}
    monkeypatch.setattr(module.model,'choose',choose)
    r=TestClient(module.app).post('/ask',json={'question':'Compare running conditions','latitude':19,'longitude':73})
    result=r.json()
    assert result['status']=='recommendation'
    assert result['best']['us_aqi']==30
    assert result['compared']['place_hour_pairs']==1
    assert all(s==source for s in result['sources'])

def test_request_timeout_returns_explicit_error(monkeypatch):
    async def timeout(*args): raise TimeoutError('Fixture timeout')
    monkeypatch.setattr(module,'recommend',timeout)
    response=TestClient(module.app).post('/ask',json={'question':'Go running tomorrow'})
    assert response.status_code==504
    assert 'no results were invented' in response.json()['detail']
