from geoai.ranking import score, context_features, suitable
from geoai.data import distance

def weather(**changes):
    return dict(apparent_temperature=25,precipitation_probability=0,wind_speed_10m=5,
                wind_direction_10m=0,weather_code=0,is_day=1,uv_index=2,**changes)

def test_thunderstorm_is_never_recommended():
    w=weather(); w['weather_code']=95
    assert 'Thunderstorm forecast' in score('running','general',w,30,[])[1]

def test_missing_air_quality_prevents_positive_recommendation():
    assert score('running','general',weather(),None,[])[1]

def test_sensitive_profile_is_more_conservative():
    assert not score('running','general',weather(),75,[])[1]
    assert score('running','asthma',weather(),75,[])[1]

def test_wind_is_from_direction_not_to_direction():
    p={'lat':0,'lon':0}
    road={'type':'way','id':1,'center':{'lat':0.001,'lon':0},'tags':{'highway':'primary'}}
    assert context_features(p,[road],0)[0]['upwind_sector']
    assert not context_features(p,[road],180)[0]['upwind_sector']

def test_unknown_wind_does_not_claim_upwind():
    p={'lat':0,'lon':0}
    road={'type':'way','id':1,'center':{'lat':0.001,'lon':0},'tags':{'highway':'primary'}}
    assert not context_features(p,[road],None)[0]['upwind_sector']

def test_tennis_requires_explicit_sport_evidence():
    assert not suitable({'tags':{'leisure':'park'}},'tennis')
    assert suitable({'tags':{'leisure':'pitch','sport':'tennis'}},'tennis')

def test_distance_units():
    assert 110<distance((0,0),(1,0))<112
