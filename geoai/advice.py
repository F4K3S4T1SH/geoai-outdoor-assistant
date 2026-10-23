from .ranking import valid_number

PREP={
 'running':['Wear visible running clothing and carry water.','Check crossings, the running surface and venue access.'],
 'cycling':['Wear a helmet, use lights and carry a puncture repair kit.','Check road crossings and the suggested bicycle route before departure.'],
 'golf':['Carry sun protection, water and appropriate footwear.','Check course access; stop play if thunder or lightning is observed.'],
 'cricket':['Carry water and the protective equipment appropriate to play.','Inspect the pitch for wet or slippery areas and check booking requirements.'],
 'football':['Carry water and footwear suited to the playing surface.','Check for waterlogging, slippery turf and pitch access.'],
 'tennis':['Carry water, sun protection and suitable court shoes.','Confirm the court is outdoors, available and dry; check lighting for evening play.'],
 'hiking':['Carry water, grippy footwear, a charged phone and an offline route.','Check trail access, recent local notices and the return time before setting off.'],
 'picnic':['Carry water, sun protection, food storage and a waste bag.','Check toilets, shelter, access rules and ground conditions.'],
 'event':['Arrange drinking water, shade and a sheltered backup location.','Confirm capacity, permissions, access and a rain contingency with the venue.'],
 'photography':['Carry weather protection for equipment and a charged battery.','Check access, footing and the return route; keep away from unsafe edges.']}

def advice_for(activity,profile,options):
    prepare=list(PREP[activity]); watch=[]
    samples=[s['weather'] for o in options for s in o.get('hourly_evidence',[{'weather':o['weather']}])]
    if profile!='general':
        prepare.append('Use your existing personal care plan; these prototype limits do not replace professional advice.')
    if any(valid_number(w.get('uv_index')) and w['uv_index']>=6 for w in samples): watch.append('Forecast UV is high in at least one compared hour; consider more coverage or another time.')
    if any(valid_number(w.get('precipitation_probability')) and w['precipitation_probability']>=25 for w in samples): watch.append('Rain is possible in the compared hours; recheck conditions and carry appropriate rain protection.')
    if any(any(f['kind']=='water' and f['distance_m']<=200 for f in o['geographic_context']) for o in options): watch.append('Mapped water is nearby: inspect barriers and footing, and supervise children closely.')
    if any(any(f['kind']=='major_road' and f['distance_m']<250 for f in o['geographic_context']) for o in options): watch.append('A major road is nearby. Traffic exposure is estimated from mapped roads and commute hours, not live congestion.')
    avoid=list(dict.fromkeys(reason for o in options for reason in o['avoid_reasons']))
    if not avoid: avoid=['Postpone if thunder or lightning is observed, conditions worsen, or venue access and ground conditions are unsuitable.']
    return {'prepare':prepare,'watch_for':watch,'avoid_when':avoid}
