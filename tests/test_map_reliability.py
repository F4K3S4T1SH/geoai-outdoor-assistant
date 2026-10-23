import asyncio
import json
import time
from geoai import data


def test_map_cache_survives_provider_cooldown(monkeypatch,tmp_path):
    monkeypatch.setattr(data,'CACHE',tmp_path)
    endpoint=data.MAP_ENDPOINTS[0]; query='fixture query'
    monkeypatch.setattr(data,'COOLDOWN',{endpoint:time.time()+30})
    data.cache_path(endpoint,{'data':query}).write_text(json.dumps({'epoch':time.time(),'data':{'elements':[]},'source':{'url':endpoint}}))
    async def fail(*a,**kw): raise AssertionError('Fresh cache must not use the network')
    monkeypatch.setattr(data,'fetch',fail)
    result,source=asyncio.run(data.overpass(query))
    assert result=={'elements':[]}
    assert source['cached'] is True


def test_corrupt_cache_is_ignored(monkeypatch,tmp_path):
    monkeypatch.setattr(data,'CACHE',tmp_path)
    data.cache_path('fixture',{}).write_text('{broken')
    assert data.read_cache('fixture',{},86400) is None


def test_osm_fallback_reconstructs_geometry_and_keeps_map_tags_only():
    raw='<osm><node id="1" lat="11" lon="76" user="private-metadata"/><node id="2" lat="11.01" lon="76.01"/><way id="3"><nd ref="1"/><nd ref="2"/><tag k="highway" v="primary"/></way><way id="4"><nd ref="1"/><tag k="building" v="yes"/></way></osm>'
    result=data.parse_osm_context(raw)
    assert len(result['elements'])==1
    assert result['elements'][0]['geometry']==[{'lat':11,'lon':76},{'lat':11.01,'lon':76.01}]
    assert 'private-metadata' not in json.dumps(result)


def test_context_uses_bounded_fallback_after_outage(monkeypatch,tmp_path):
    monkeypatch.setattr(data,'CACHE',tmp_path)
    async def outage(*a,**kw): raise data.SourceError('Fixture outage')
    async def fallback(url,params,**kw):
        assert url=='https://api.openstreetmap.org/api/0.6/map'
        west,south,east,north=map(float,params['bbox'].split(','))
        assert (east-west)*(north-south)<.002
        assert kw['ttl']==86400
        return {'elements':[],'context_available':True},{'url':url}
    monkeypatch.setattr(data,'overpass',outage)
    monkeypatch.setattr(data,'fetch',fallback)
    result,source=asyncio.run(data.context(11.4,76.7))
    assert result['context_available']
    assert 'fallback' in source['note']


def test_venue_search_ignores_park_named_streets_and_uses_real_map(monkeypatch):
    async def outage(*a,**kw): raise data.SourceError('Fixture outage')
    async def streets(*a,**kw): return [{'name':'Park Road','tags':{'highway':'residential'}}],{'url':'fixture'}
    async def extract(*a): return {'elements':[{'type':'way','id':3,'center':{'lat':11.4,'lon':76.7},'tags':{'leisure':'park','name':'Mapped fixture park'}}]},{'url':'fixture map'}
    monkeypatch.setattr(data,'overpass',outage)
    monkeypatch.setattr(data,'photon_places',streets)
    monkeypatch.setattr(data,'map_extract',extract)
    places,source=asyncio.run(data.places(11.4,76.7,5,'picnic'))
    assert [p['name'] for p in places]==['Mapped fixture park']
    assert places[0]['id']=='way/3'
    assert 'not the entire requested radius' in places[0]['map_note']


def test_context_does_not_mistake_paths_or_sports_pitches_for_roads_or_greenery():
    from geoai.ranking import context_features
    elements=[{'type':'way','id':i,'tags':tags,'geometry':[{'lat':11.4,'lon':76.7}]} for i,tags in enumerate([{'highway':'path'},{'leisure':'pitch'},{'leisure':'park'}])]
    assert [f['kind'] for f in context_features({'lat':11.4,'lon':76.7},elements,0)]==['green_cover']

def test_dense_map_extract_retries_once_at_smaller_disclosed_extent(monkeypatch):
    calls=[]
    async def fetch(url,params,**kwargs):
        calls.append(params['bbox'])
        if len(calls)==1: raise data.SourceError(url+': 400')
        return {'elements':[],'context_available':True},{'url':url}
    monkeypatch.setattr(data,'fetch',fetch)
    result,source=asyncio.run(data.map_extract(11.93,79.83))
    assert len(calls)==2
    assert '500 m' in result['coverage_note']
    assert source['coverage_note']==result['coverage_note']
