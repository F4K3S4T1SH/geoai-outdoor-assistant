import asyncio
import httpx
import pytest
from geoai import data

@pytest.mark.parametrize('status',[200,429])
def test_weather_reconnects_once_but_respects_http_rate_limit(monkeypatch,tmp_path,status):
    calls=[]
    url='https://air-quality-api.open-meteo.com/v1/air-quality'
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,target,**kwargs):
            calls.append(target)
            request=httpx.Request('GET',target)
            if status==200 and len(calls)==1: raise httpx.ConnectTimeout('Transient fixture',request=request)
            return httpx.Response(status,json={'hourly':{'time':[]}},request=request)
    monkeypatch.setattr(data,'CACHE',tmp_path)
    monkeypatch.setattr(data.httpx,'AsyncClient',Client)
    if status==429:
        with pytest.raises(data.SourceError): asyncio.run(data.fetch(url,{}))
        assert len(calls)==1
    else:
        result,source=asyncio.run(data.fetch(url,{}))
        assert len(calls)==2 and result['hourly']['time']==[]
