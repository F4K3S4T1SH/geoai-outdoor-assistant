from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from geoai import app as module
from geoai.intent import normalize
from geoai.ranking import score,suitable

@pytest.mark.parametrize('activity,tags',[
 ('running',{'leisure':'park'}),('cycling',{'highway':'cycleway'}),('golf',{'leisure':'golf_course'}),
 ('cricket',{'leisure':'pitch','sport':'cricket'}),('football',{'leisure':'pitch','sport':'soccer'}),
 ('tennis',{'leisure':'pitch','sport':'tennis'}),('hiking',{'highway':'path'}),('picnic',{'tourism':'picnic_site'}),
 ('event',{'leisure':'park'}),('photography',{'tourism':'viewpoint'})])
@pytest.mark.parametrize('storm',[False,True])
@pytest.mark.parametrize('context_missing',[False,True])
def test_each_activity_can_complete_grounded_flow(monkeypatch,activity,tags,storm,context_missing):
    now=datetime.now(module.TZ); t=(now+timedelta(hours=2)).replace(minute=0,second=0,microsecond=0)
    s={'url':'synthetic test fixture, not live data'}
    async def extract(*_): return {'activity':activity,'profile':'general','start':t.isoformat(),'end':(t+timedelta(hours=2)).isoformat()}
    async def places(*_): return [{'id':'fixture','name':'Fixture outdoor venue','lat':19,'lon':73,'distance_km':1,'tags':tags}],s
    async def weather(*_): return {'hourly':{'time':[(t+timedelta(hours=i)).replace(tzinfo=None).isoformat(timespec='minutes') for i in range(2)],'temperature_2m':[24,24],'apparent_temperature':[24,24],'precipitation_probability':[0,0],'wind_speed_10m':[5,5],'wind_direction_10m':[0,0],'weather_code':[0,95 if storm else 0],'is_day':[1,1],'uv_index':[2,2]}},s
    async def air(*_): return {'hourly':{'time':[(t+timedelta(hours=i)).replace(tzinfo=None).isoformat(timespec='minutes') for i in range(2)],'us_aqi':[30,30]}},s
    async def context(*_):
        if context_missing: raise module.data.SourceError('Map unavailable in fixture')
        return {'elements':[]},s
    async def route(*_): return {'distance_km':1.2,'duration_minutes':8,'mode':'bicycle','geometry':{'type':'LineString','coordinates':[[73,19],[73.01,19.01]]}},s
    async def choose(*_): return 0,{'us_aqi':30}
    monkeypatch.setattr(module.model,'extract',extract); monkeypatch.setattr(module.model,'choose',choose)
    for key,value in [('places',places),('forecast',weather),('air',air),('context',context),('route',route)]: monkeypatch.setattr(module.data,key,value)
    r=TestClient(module.app).post('/ask',json={'question':'Compare outdoor conditions','latitude':19,'longitude':73,'duration_minutes':120})
    assert r.status_code==200,r.text
    assert r.json()['status']==('avoid_or_insufficient_data' if storm or context_missing else 'recommendation'),r.json()
    assert r.json()['guidance']['prepare']
    result=r.json()
    assert result['compared']['venues_with_forecast']==1
    assert result['compared']['venues_with_evidence']==(0 if context_missing else 1)
    assert result['outcome']['kind']==('mixed' if storm and context_missing else 'incomplete_checks' if context_missing else 'conditions_unsuitable' if storm else 'recommendation')
    if not storm and not context_missing: assert result['best']['hourly_evidence'][0]['us_aqi']==30
    if storm: assert any('Thunderstorm forecast' in o['condition_reasons'] for o in result['avoided_options'])
    if context_missing:
        assert result['best'] is None
        assert all(o['checks_missing'] and o['assessment']=='incomplete' for o in result['avoided_options'])

def test_weekend_and_profile_normalization():
    now=datetime(2026,10,23,tzinfo=ZoneInfo('Asia/Kolkata'))
    parsed=normalize({'profile':'general'},'picnic this weekend in the morning for my 8 year-old child',now)
    assert parsed['start']=='2026-10-24T06:00'
    assert parsed['end']=='2026-10-25T10:00'
    assert parsed['hours']==[6,10]
    assert parsed['profile']=='child'

def test_explicit_clock_overrides_hallucinated_model_clock():
    parsed=normalize({'duration_minutes':60},'run tomorrow at 8 AM',datetime(2026,10,23,tzinfo=ZoneInfo('Asia/Kolkata')))
    assert parsed['start']=='2026-10-24T08:00'
    assert parsed['end']=='2026-10-24T09:00'

def test_green_water_and_traffic_affect_scores():
    w=dict(apparent_temperature=25,precipitation_probability=0,wind_speed_10m=5,weather_code=0,is_day=1,uv_index=2)
    baseline=score('picnic','general',w,30,[])[0]
    green=score('picnic','general',w,30,[{'kind':'green_cover','distance_m':100}])[0]
    water=score('picnic','general',w,30,[{'kind':'water','distance_m':100}])[0]
    roads=[{'kind':'major_road','distance_m':100,'upwind_sector':False}]
    morning=score('picnic','general',w,30,roads,when=datetime(2026,10,23,8))[0]
    midday=score('picnic','general',w,30,roads,when=datetime(2026,10,23,12))[0]
    assert green>baseline>water
    assert morning<midday

def test_indoor_tennis_is_rejected():
    assert not suitable({'tags':{'sport':'tennis','indoor':'yes'}},'tennis')
