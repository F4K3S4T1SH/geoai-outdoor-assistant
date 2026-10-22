"""Enforce explicit relative dates and profile words independently of SLM output."""
import re
from datetime import datetime,timedelta,time

def normalize(intent,question,now):
    out=dict(intent); text=question.lower()
    for k in ('location','start','end','clarification'):
        if out.get(k) in ('null','None','question or null','place name or null'): out[k]=None
    for profile,pattern in [('asthma',r'\basthma\b|\basthmatic\b'),('pregnancy',r'\bpregnan'),
                            ('child',r'\bkids?\b|\bchild(?:ren)?\b'),('senior',r'\bseniors?\b|\belderly\b')]:
        if re.search(pattern,text): out['profile']=profile; break
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
    if day is not None:
        ranges=[('morning',6,10),('afternoon',12,16),('evening',16,19),('tonight',18,23)]
        chosen=next(((a,b) for word,a,b in ranges if word in text),None)
        explicit_clock=bool(re.search(r'\b\d{1,2}(?::\d{2}|\s*(?:am|pm))\b',text))
        if chosen and not explicit_clock:
            out['start']=datetime.combine(day,time(chosen[0])).isoformat(timespec='minutes')
            out['end']=datetime.combine(day,time(chosen[1])).isoformat(timespec='minutes')
        else:
            for key in ('start','end'):
                if out.get(key):
                    try: out[key]=datetime.fromisoformat(out[key]).replace(year=day.year,month=day.month,day=day.day).isoformat()
                    except (ValueError,TypeError): out[key]=None
    return out
