"""Enforce explicit relative dates and profile words independently of SLM output."""
import re
import math
from datetime import datetime,timedelta,time

def normalize(intent,question,now):
    out=dict(intent); text=question.lower()
    numbers={'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'fifteen':15,'twenty':20,'thirty':30,'forty':40}
    text=re.sub(r'\b('+'|'.join(numbers)+r')(?=\s*[- ]?\s*(?:kms?\b|kilomet(?:er|re)s?\b|hours?\b|hrs?\b|minutes?\b|mins?\b|am\b|pm\b))',lambda m:str(numbers[m[0]]),text)
    aliases={'walking':'hiking','walk':'hiking','nature_walk':'hiking','jogging':'running','jog':'running','soccer':'football','outdoor_event':'event','photography_session':'photography'}
    out['activity']=aliases.get(out.get('activity'),out.get('activity'))
    # Anchor unambiguous explicit activity words; the SLM handles the remaining
    # free-form intent, while it cannot turn a plain walk into a run.
    activity_words={'running':r'\b(?:run|running|jog|jogging)\b',
        'cycling':r'\b(?:cycle|cycling|bike|biking|bicycle)\b',
        'golf':r'\bgolf\b','cricket':r'\bcricket\b','football':r'\b(?:football|soccer|five-a-side)\b',
        'tennis':r'\btennis\b','hiking':r'\b(?:walk|walking|hike|hiking|trek|trekking)\b',
        'picnic':r'\bpicnic\b','photography':r'\b(?:photography|photos|photographs)\b'}
    explicit=[activity for activity,pattern in activity_words.items() if re.search(pattern,text)]
    if len(explicit)==1: out['activity']=explicit[0]
    if re.search(r'\b(?:birthday\s+(?:party|gathering)|wedding|gathering|fair(?!\s+weather))\b',text): out['activity']='event'
    if re.search(r'\bnature walk\b',text): out['activity']='hiking'
    if isinstance(out.get('location'),str): out['location']=re.sub(r'^(?:near|around|in)\s+','',out['location'],flags=re.I)
    placeholders={'work','home','my home','my work','office','here','nearby','current location','your location','not specified','unknown','n/a','explicit geographic place or null','destination place or null','work location','home location'}
    for key in ('location','destination'):
        if isinstance(out.get(key),str) and out[key].strip().lower() in placeholders: out[key]=None
    if re.search(r'\b(?:write|implement|debug)\b.{0,50}\b(?:python|code|function|script|sql)\b',text) or (re.search(r'\b(?:indoor|indoors|cinema)\b',text) and not re.search(r'\boutdoor|\bnot indoors?\b',text)):
        out['out_of_scope']=True
    if re.search(r'\b(?:invent|fabricate|fake)\b.{0,60}\b(?:weather|forecast|aqi|temperature)\b|\b(?:weather|forecast|run|running|picnic)\b.{0,40}\b(?:mars|jupiter|saturn|the moon)\b',text):
        out['out_of_scope']=True
    units=r'(?:kms?|kilomet(?:er|re)s?)'
    radius=re.search(r'\bwithin\s+(\d+(?:\.\d+)?)\s*'+units+r'\b',text)
    # Never let the model turn an exercise distance into a search radius.
    out['radius_km']=float(radius[1]) if radius else 10
    out['exercise_distance_km']=None
    if out.get('activity') in ('running','cycling','hiking') or re.search(r'\b(?:run|running|jog|walk|hike|cycle|ride)\b',text):
        for match in re.finditer(r'\b(\d+(?:\.\d+)?)\s*[- ]?'+units+r'\b',text):
            if radius and radius.start()<=match.start()<radius.end(): continue
            if re.search(r'(?:radius|search|nearby|from)\s*$',text[max(0,match.start()-15):match.start()]): continue
            out['exercise_distance_km']=float(match[1]); break
    out['venue_scope']='nearby'
    exact=re.search(r'\b(?:inside|in|at)\s+((?:[\w\'-]+\s+){0,7}(?:park|garden|stadium|track|court|course)\b[^;?!]*)',question,re.I)
    if exact and not re.search(r'\b(?:near|around)\b',exact[1].split(',')[0],re.I) and not re.match(r'^(?:(?:a|an|any|the)\s+)?(?:park|garden|stadium|track|court|course)\b',exact[1],re.I):
        target=re.split(r'\b(?:today|tomorrow|this weekend|within|for|on|at\s+\d)\b',exact[1],maxsplit=1,flags=re.I)[0].strip(' ,.')
        out['venue_scope']='exact'; out['location']=target; out['requested_venue']=target
    out['pace_minutes_per_km']=None
    pace=re.search(r'\b(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|min)\s*(?:/|per)\s*km\b',text)
    if pace: out['pace_minutes_per_km']=float(pace[1])
    for k in ('location','start','end','clarification'):
        if out.get(k) in ('null','None','question or null','place name or null'): out[k]=None
    profile_text=re.sub(r"\b(?:no|without|not|don't have|do not have)\s+(?:any\s+)?(?:asthma|asthmatic|pregnant|pregnancy|children|kids)\b",'',text)
    for name,pattern in [('asthma',r'\basthma\b|\basthmatic\b'),('pregnancy',r'\bpregnan'),('child',r'\bkids?\b|\bchild(?:ren)?\b')]:
        if re.search(pattern,text) and not re.search(pattern,profile_text) and out.get('profile')==name: out['profile']='general'
    for profile,pattern in [('asthma',r'\basthma\b|\basthmatic\b'),('pregnancy',r'\bpregnan'),
                            ('child',r'\bkids?\b|\bchild(?:ren)?\b'),('senior',r'\bseniors?\b|\belderly\b')]:
        if re.search(pattern,profile_text): out['profile']=profile; break
    ages=[int(x) for x in re.findall(r'\b(\d{1,3})\s*[- ]?\s*(?:years?[- ]old|yrs?[- ]old)',text)]
    if ages:
        out['age']=ages[0]
        out['invalid_age']=any(age>120 for age in ages)
        if out.get('profile') in (None,'general'):
            if min(ages)<16: out['profile']='child'
            elif max(ages)>=65: out['profile']='senior'
    if re.search(r'\b(?:parents|mother|father|mum|mom|dad)\b',text) and not ages and not re.search(r'\b(?:senior|elderly|asthma|asthmatic|pregnan|child|kids)',profile_text):
        out['profile']='general'; out['confirm_family_profile']=True
    if re.search(r'\bcommut|\bcycle to work|\bcycling to work',text): out['mode']='commute'
    travel=re.search(r'\b(?:travel|journey|drive)(?:\s+time)?\s+(?:under|within|up to|less than|no more than)\s+(\d+)\s*(?:minutes?|mins?)\b',text)
    out['max_travel_minutes']=int(travel[1]) if travel else None
    duration_text=text[:travel.start()]+text[travel.end():] if travel else text
    duration=re.search(r'\b(?:for\s+)?(one|two|three|four|half|\d+(?:\.\d+)?)\s*[- ]?\s*(hours?|hrs?|minutes?|mins?)\b(?!\s*(?:/|per)\s*km)',duration_text)
    out['duration_explicit']=duration is not None
    if duration:
        number={'one':1,'two':2,'three':3,'four':4,'half':.5}.get(duration[1])
        if number is None: number=float(duration[1])
        out['duration_minutes']=round(number*(60 if duration[2].startswith(('hour','hr')) else 1))
    else: out['duration_minutes']=60
    if out['exercise_distance_km'] is not None and out['pace_minutes_per_km'] is not None and not out['duration_explicit']:
        out['duration_minutes']=math.ceil(out['exercise_distance_km']*out['pace_minutes_per_km'])
    day=None
    if re.search(r'\btomorrow\b',text): day=now.date()+timedelta(days=1)
    elif re.search(r'\btoday\b|\btonight\b|\bthis (?:morning|afternoon|evening)\b',text): day=now.date()
    elif 'weekend' not in text:
        weekdays=['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
        for i,name in enumerate(weekdays):
            if re.search(r'\b'+name+r'\b',text):
                delta=(i-now.weekday())%7
                if delta==0: delta=7
                day=now.date()+timedelta(days=delta); break
    absolute=re.search(r'\b(20\d{2}-\d{2}-\d{2})\b',text)
    if absolute:
        try: day=datetime.fromisoformat(absolute[1]).date()
        except ValueError: out['start']=out['end']=None; out['invalid_date']=True
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
            out['assumptions']=['No part of day was specified; comparing 06:00â€“20:00 IST.']
        clocks=list(re.finditer(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',text))
        if not clocks:
            clocks=list(re.finditer(r'\b([01]?\d|2[0-3]):([0-5]\d)(?!\s*(?:am|pm))\b',text))
            clock24=True
        else: clock24=False
        if clocks:
            def clock(m): return time(int(m[1]),int(m[2])) if clock24 else time((int(m[1])%12)+(12 if m[3]=='pm' else 0),int(m[2] or 0))
            if not clock24 and any(not 1<=int(m[1])<=12 or int(m[2] or 0)>59 for m in clocks):
                out['start']=out['end']=None
                out['invalid_date']=True
                return out
            start_dt=datetime.combine(day,clock(clocks[0])); duration=out.get('duration_minutes') or 60
            out['start']=start_dt.isoformat(timespec='minutes')
            end_dt=datetime.combine(end_day or day,clock(clocks[1])) if len(clocks)>1 else start_dt+timedelta(minutes=duration)
            if end_dt<=start_dt: end_dt+=timedelta(days=1)
            out['end']=end_dt.isoformat(timespec='minutes')
            out.pop('hours',None)
    if day is None and not re.search(r'\b(?:in \d+ hours?|next week|next weekend)\b',text):
        out['start']=None; out['end']=None
    if 'sunset' in text: out['sunset_only']=True
    return out
