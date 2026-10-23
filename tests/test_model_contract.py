import asyncio
import json
import httpx
import pytest
from geoai import model

@pytest.mark.parametrize('payload',[
    {}, {'choices':[]}, {'choices':[{}]},
    {'choices':[{'message':{'content':'not JSON'}}]},
    {'choices':[{'message':{'content':'[]'}}]},
    {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]},
])
def test_bad_model_output_never_becomes_a_plan(monkeypatch,payload):
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,**kwargs):
            return httpx.Response(200,json=payload,request=httpx.Request('POST',url))
    monkeypatch.setattr(model.httpx,'AsyncClient',Client)
    with pytest.raises(model.ModelError): asyncio.run(model.structured([],{}))

def test_structured_request_enforces_schema_and_disables_thinking(monkeypatch):
    seen={}
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,**kwargs):
            seen.update(kwargs['json'])
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'ok':True})}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(model.httpx,'AsyncClient',Client)
    assert asyncio.run(model.structured([],{'type':'object'}))=={'ok':True}
    assert seen['temperature']==0
    assert seen['response_format']['json_schema']['strict'] is True
    assert seen['chat_template_kwargs']['thinking'] is False
