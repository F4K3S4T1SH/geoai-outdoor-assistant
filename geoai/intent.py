"""Enforce explicit relative dates and profile words independently of SLM output."""
import re
from datetime import datetime,timedelta,time

def normalize(intent,question,now):
    out=dict(intent); text=question.lower()
    aliases={'walking':'hiking','walk':'hiking','nature_walk':'hiking','jogging':'running','jog':'running','soccer':'football','outdoor_event':'event','photography_session':'photography'}
    out['activity']=aliases.get(out.get('activity'),out.get('activity'))
    if re.search(r'\b(?:birthday|wedding|gathering|fair)\b',text): out['activity']='event'
    if re.search(r'\bnature walk\b',text): out['activity']='hiking'
    if isinstance(out.get('location'),str): out['location']=re.sub(r'^(?:near|around|in)\s+','',out['location'],flags=re.I)
    radius=re.search(r'\bwithin\s+(\d+(?:\.\d+)?)\s*(?:km|kilomet(?:er|re)s?)\b',text)
    if radius: out['radius_km']=float(radius[1])
    for k in ('location','start','end','clarification'):
        if out.get(k) in ('null','None','question or null','place name or null'): out[k]=None
    for profile,pattern in [('asthma',r'\basthma\b|\basthmatic\b'),('pregnancy',r'\bpregnan'),
                            ('child',r'\bkids?\b|\bchild(?:ren)?\b'),('senior',r'\bseniors?\b|\belderly\b')]:
        if re.search(pattern,text): out['profile']=profile; break
    ages=[int(x) for x in re.findall(r'\b(\d{1,3})\s*(?:years? old|year-old|yrs? old)',text)]
    if ages:
        out['age']=ages[0]
        if out.get('profile') in (None,'general'):
            if min(ages)<16: out['profile']='child'
            elif max(ages)>=65: out['profile']='senior'
    if re.search(r'\bcommut|\bcycle to work|\bcycling to work',text): out['mode']='commute'
    duration=re.search(r'\b(?:for\s+)?(one|two|three|four|half|\d+(?:\.\d+)?)\s*[- ]?\s*(hours?|hrs?|minutes?|mins?)\b',text)
    if duration:
        number={'one':1,'two':2,'three':3,'four':4,'half':.5}.get(duration[1])
        if number is None: number=float(duration[1])
        out['duration_minutes']=min(360,max(15,round(number*(60 if duration[2].startswith(('hour','hr')) else 1))))
    else: out['duration_minutes']=60
    day=None
    if re.search(r'\btomorrow\b',text): day=now.date()+timedelta(days=1)
    elif re.search(r'\btoday\b|\btonight\b',text): day=now.date()
    elif 'weekend' not in text:
        weekdays=['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        for i,name in enumerate(weekdays):
            if re.search(r'\b'+name+r'\b',text):
                delta=(i-now.weekday())%7
                if delta==0: delta=7
                day=now.date()+timedelta(days=delta); break
    end_day=day
    if 'this weekend' in text or ('saturday' in text and 'sunday' in text):
        delta=(5-now.weekday())%7
        day=now.date()+timedelta(days=delta) if now.weekday()!=6 else now.date()
        end_day=day+timedelta(days=1) if day.weekday()==5 else day
    multi=re.search(r'next\s+(two|three|four|five|[2-5])\s+days',text)
    if multi:
        count={'two':2,'three':3,'four':4,'five':5}.get(multi[1],int(multi[1]) if multi[1].isdigit() else 2)
        day=now.date(); end_day=day+timedelta(days=count-1)
    if day is not None:
        ranges=[('morning',6,10),('afternoon',12,16),('evening',16,19),('after work',17,20),('tonight',18,23)]
        chosen=next(((a,b) for word,a,b in ranges if word in text),None)
        explicit_clock=bool(re.search(r'\b\d{1,2}(?::\d{2}|\s*(?:am|pm))\b',text))
        if chosen and not explicit_clock:
            out['start']=datetime.combine(day,time(chosen[0])).isoformat(timespec='minutes')
            out['end']=datetime.combine(end_day or day,time(chosen[1])).isoformat(timespec='minutes')
            out['hours']=[chosen[0],chosen[1]]
        else:
            for key in ('start','end'):
                if out.get(key):
                    try: out[key]=datetime.fromisoformat(out[key]).replace(year=day.year,month=day.month,day=day.day).isoformat()
                    except (ValueError,TypeError): out[key]=None
        if not chosen and not explicit_clock:
            out['start']=datetime.combine(day,time(6)).isoformat(timespec='minutes')
            out['end']=datetime.combine(end_day or day,time(20)).isoformat(timespec='minutes')
            out['assumptions']=['No part of day was specified; comparing 06:00–20:00 IST.']
        clocks=list(re.finditer(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',text))
        if clocks:
            def clock(m): return time((int(m[1])%12)+(12 if m[3]=='pm' else 0),int(m[2] or 0))
            start_dt=datetime.combine(day,clock(clocks[0])); duration=out.get('duration_minutes') or 60
            out['start']=start_dt.isoformat(timespec='minutes')
            out['end']=(datetime.combine(end_day or day,clock(clocks[1])) if len(clocks)>1 else start_dt+timedelta(minutes=duration)).isoformat(timespec='minutes')
            out.pop('hours',None)
    if 'sunset' in text: out['sunset_only']=True
    return out
