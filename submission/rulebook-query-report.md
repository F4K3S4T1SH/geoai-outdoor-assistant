# Rulebook example-query test — Team NEXA

Recorded 2026-10-23T22:23:08.485906+05:30 (IST). All ten page-3 example questions were first sent unchanged to the public API. Missing details were then supplied as explicitly recorded test choices, without changing the question text.

**Verdict: 10/10 core interpretation checks passed; full live coverage is not completely verified.** Twenty HTTP requests returned valid HTTP 200 responses: three recommendations, four condition-based declines, two past-time clarifications, one golf-coverage gap. A decline is not a parsing failure, and a valid HTTP response alone does not prove recommendation quality.

| # | Rulebook example | Live observation |
|---|---|---|
| 1 | Where can I go running tomorrow evening near Koregaon Park? | Declined on AQI/daylight limits; one venue lacked geographic context. |
| 2 | Best time this weekend for a kids' cricket match within 15 km of Whitefield? | Recommended Willow Sports Cricket academy on Sunday 25 October at 07:00 IST, child profile, US AQI 48. One other venue lacked geographic context. |
| 3 | I have mild asthma, where's good for a morning walk near Powai in the next two days? | Declined on stricter asthma AQI/heat limits; two venues lacked geographic context. |
| 4 | Is it okay to cycle to work at 8 AM? | Original question asked for missing origin. After explicit test origin/destination/date: recommended the Cubbon Park to Vidhana Soudha commute at 08:00 on 24 October; US AQI 53. |
| 5 | Planning an outdoor birthday party on Sunday afternoon in Pune, what should I keep in mind? | Declined on AQI/heat limits; complete checks for two compared venues. |
| 6 | Good place and time for golf on Saturday within 40 km of Andheri? | Unresolved coverage gap: map-search fallback checked about 1 km, not the requested 40 km. No verified golf venue; cannot call the full example verified. |
| 7 | Where can I take sunset photos this evening around Bandra? | After location confirmation, asked for a future interval. This evening had already passed at test time. |
| 8 | Is Saturday or Sunday better for a hike near Lonavala? | Compared Saturday and Sunday (114 venue/time pairs); declined on AQI/daylight limits with complete checks for three compared venues. |
| 9 | When is it safe for my parents to walk outdoors tomorrow in Bengaluru? | Original question asked for parents' age/profile. After explicit senior test profile and Bengaluru search centre: recommended Park at RT Nagar on 24 October at 07:00 IST, US AQI 45. |
| 10 | Outdoor tennis after work today near Hinjewadi, any good spots? | After location confirmation, asked for a future interval. Today's after-work window had already passed. |

## Test method and limits

- All unchanged questions initially requested clarification: eight place confirmations, one missing commute origin, one unspecified parents profile.
- Followups use disclosed test choices, not inferred personal addresses or health facts.
- The live provider response changes over time. No general accuracy, universal coverage or future uptime guarantee.
- Golf coverage is not fully verified; fallback around 1 km did not cover the requested 40 km.
- Some other venues lacked geographic context. Positive recommendations only used complete evidence for the chosen option.
- Unspecified activity duration defaults to one hour, explicitly disclosed by the application.

Evidence in the public source repository: submission/rulebook-query-evaluation.json (unchanged first requests), submission/rulebook-followup-evaluation.json (test choices and live responses), submission/rulebook-query-summary.json (compact results). Test questions are outside the runtime answer path; no example response is hard-coded.

Source: user-supplied geoai-hackathon-2026-rulebook.pdf, page 3.
