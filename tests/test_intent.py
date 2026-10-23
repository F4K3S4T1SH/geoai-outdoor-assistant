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

def test_overnight_clock_range_crosses_midnight():
    out=normalize({},'photography tomorrow 9pm to 1am',NOW)
    assert out['start']=='2026-10-24T21:00'
    assert out['end']=='2026-10-25T01:00'

def test_invalid_clock_is_not_silently_wrapped():
    out=normalize({},'run tomorrow at 99am',NOW)
    assert out['start'] is None
    assert out['invalid_date'] is True

def test_explicit_walk_cannot_be_changed_to_running_by_model():
    out=normalize({'activity':'running'},'My parents want a walk tomorrow in Bengaluru',NOW)
    assert out['activity']=='hiking'

def test_placeholder_addresses_cannot_become_commute_endpoints():
    out=normalize({'location':'explicit geographic place or null','destination':'work location'},'Cycle to work tomorrow at 8am',NOW)
    assert out['location'] is None and out['destination'] is None

def test_written_numbers_preserve_radius_and_clock():
    out=normalize({},'walk tomorrow at eight am within five kilometres of Powai',NOW)
    assert out['radius_km']==5
    assert out['start']=='2026-10-24T08:00'

def test_written_distance_is_not_search_radius():
    out=normalize({},'ten km run tomorrow at 8am at six min/km near Powai',NOW)
    assert out['exercise_distance_km']==10
    assert out['radius_km']==10
    assert out['duration_minutes']==60

def test_written_long_duration_is_not_truncated():
    assert normalize({},'hike for seven hours tomorrow',NOW)['duration_minutes']==420
