from datetime import datetime
from zoneinfo import ZoneInfo
from geoai.intent import normalize

NOW=datetime(2026,10,23,0,30,tzinfo=ZoneInfo('Asia/Kolkata'))

def test_tomorrow_never_means_today():
    out=normalize({'start':'2026-10-23T16:00','end':'2026-10-23T19:00'},'run tomorrow evening',NOW)
    assert out['start']=='2026-10-24T16:00'
    assert out['end']=='2026-10-24T19:00'

def test_explicit_asthma_cannot_be_dropped():
    out=normalize({'profile':'general'},'I have mild asthma, walk tomorrow morning',NOW)
    assert out['profile']=='asthma'
    assert out['end']=='2026-10-24T10:00'

def test_incomplete_question_stays_incomplete():
    out=normalize({'location':'null','start':None,'end':None},'can I go running?',NOW)
    assert out['location'] is None
    assert out['start'] is None

def test_next_saturday():
    assert normalize({},'cricket Saturday afternoon',NOW)['start']=='2026-10-24T12:00'
