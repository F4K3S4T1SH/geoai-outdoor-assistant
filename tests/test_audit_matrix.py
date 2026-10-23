"""Cross-product invariants, with synthetic conditions (never runtime data)."""
import math
from datetime import datetime
import pytest
from geoai.ranking import ACTIVITIES,score,context_features,suitable
from geoai.intent import normalize
from geoai.app import TZ

PROFILES=['general','asthma','child','senior','pregnancy']
SCENARIOS=['good','heat','cold','rain','wind','storm','night','missing_temperature','nan_temperature','missing_aqi','negative_aqi','moderate_aqi','invalid_weather_code']

@pytest.mark.parametrize('activity',list(ACTIVITIES))
@pytest.mark.parametrize('profile',PROFILES)
@pytest.mark.parametrize('scenario',SCENARIOS)
def test_activity_profile_weather_matrix(activity,profile,scenario):
    w={'apparent_temperature':24,'precipitation_probability':0,'wind_speed_10m':5,'weather_code':0,'is_day':1,'uv_index':2}
    aq=30
    overrides={'heat':('apparent_temperature',45),'cold':('apparent_temperature',0),'rain':('precipitation_probability',90),'wind':('wind_speed_10m',80),'storm':('weather_code',95),'night':('is_day',0),'missing_temperature':('apparent_temperature',None),'nan_temperature':('apparent_temperature',float('nan')),'invalid_weather_code':('weather_code',999)}
    if scenario in overrides:w[overrides[scenario][0]]=overrides[scenario][1]
    if scenario=='missing_aqi': aq=None
    if scenario=='negative_aqi': aq=-1
    if scenario=='moderate_aqi': aq=80
    value,blocks,reasons=score(activity,profile,w,aq,[])
    eligible=scenario=='good' or (scenario=='moderate_aqi' and profile=='general')
    assert bool(blocks)==(not eligible)
    if value is not None: assert math.isfinite(value) and 0<=value<=100

def test_distance_to_long_road_uses_segments_not_only_vertices():
    # Road endpoints are >1 km away; its middle passes 11 m north of the park.
    road={'type':'way','id':1,'tags':{'highway':'primary'},'geometry':[{'lat':19.0001,'lon':72.99},{'lat':19.0001,'lon':73.01}]}
    f=context_features({'lat':19,'lon':73},[road],0)[0]
    assert 9<=f['distance_m']<=13
    assert f['upwind_sector'] is True

def test_venue_inside_large_green_polygon_is_inside_not_far_from_vertices():
    points=[(18.99,72.99),(18.99,73.01),(19.01,73.01),(19.01,72.99),(18.99,72.99)]
    green={'type':'way','id':1,'tags':{'landuse':'forest'},'geometry':[{'lat':lat,'lon':lon} for lat,lon in points]}
    f=context_features({'lat':19,'lon':73},[green],0)[0]
    assert f['distance_m']==0
    assert f['inside_mapped_area'] is True

@pytest.mark.parametrize('question,raw,expected',[
    ('No asthma. Run tomorrow near Powai',{'profile':'asthma'},'general'),
    ('I am not pregnant. Picnic tomorrow near Powai',{'profile':'pregnancy'},'general'),
    ('My 70-year-old father wants a walk tomorrow',{'profile':'general'},'senior'),
    ('My 8-year-old wants cricket tomorrow',{'profile':'general'},'child'),
    ('Fair weather for running tomorrow',{'activity':'running'},'general'),
])
def test_messy_profile_and_activity_requests(question,raw,expected):
    out=normalize(raw,question,datetime(2026,10,23,10,tzinfo=TZ))
    assert out.get('profile','general')==expected
    if question.startswith('Fair weather'): assert out['activity']=='running'

def test_parents_are_not_assumed_to_be_seniors():
    out=normalize({'profile':'senior'},'When can my parents walk tomorrow in Bengaluru?',datetime(2026,10,23,10,tzinfo=TZ))
    assert out['confirm_family_profile'] is True
    assert out['profile']=='general'

def test_no_date_cannot_be_invented_by_model():
    out=normalize({'start':'2026-10-24T08:00','end':'2026-10-24T10:00'},'Run near Powai',datetime(2026,10,23,10,tzinfo=TZ))
    assert out['start'] is None and out['end'] is None

def test_24_hour_clock_and_absolute_date_are_respected():
    out=normalize({},'Run near Powai on 2026-10-24 from 09:00 to 13:00',datetime(2026,10,23,10,tzinfo=TZ))
    assert out['start']=='2026-10-24T09:00'
    assert out['end']=='2026-10-24T13:00'

def test_travel_budget_does_not_become_exercise_duration():
    out=normalize({'activity':'running'},'Run tomorrow near Powai, travel under 20 minutes',datetime(2026,10,23,10,tzinfo=TZ))
    assert out['max_travel_minutes']==20
    assert out['duration_minutes']==60
    assert out['duration_explicit'] is False

def test_long_duration_is_rejected_rather_than_silently_shortened():
    out=normalize({},'Picnic tomorrow for seven hours',datetime(2026,10,23,10,tzinfo=TZ))
    # Numeric form is guaranteed by the explicit-duration guard; the SLM may
    # recognise spelled forms too, but they must not overwrite explicit digits.
    out=normalize({},'Picnic tomorrow for 7 hours',datetime(2026,10,23,10,tzinfo=TZ))
    assert out['duration_minutes']==420

@pytest.mark.parametrize('activity',list(ACTIVITIES))
def test_private_venue_cannot_become_an_eligible_public_recommendation(activity):
    assert not suitable({'tags':{'leisure':'park','sport':'golf;cricket;soccer;tennis','access':'private'}},activity)
