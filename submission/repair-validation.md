# Map reliability and result wording repair

Verified 23 October 2026 IST, application version 0.2.2.

- 67 automated checks passed. These include all ten activities with good conditions, second-hour storms and missing map evidence; missing wind direction; fresh cache during provider cooldown; corrupt cache; OSM XML geometry; and a park-named street search fallback.
- Public HTTPS `/ask` returned HTTP 200 in 20.12 seconds for a 30-minute picnic near Cubbon Park, Bengaluru tomorrow morning. Five venues had complete weather, AQI and geographic checks, 20 place/time pairs were compared, no data failures were reported, and Rose Garden was selected with alternatives. See `repair-live-example.json`. The result retains rain and AQI cautions and discloses the smaller fallback search coverage. This was tested from the host laptop, not an independent external machine.
- A browser test around Ooty completed all four venues' checks and 16 place/time pairs. The picnic was declined due to forecast rain/daylight conditions, without the previous missing-map failures.
- Browser inspection confirmed recommendation cards, alternatives, map attribution, accurate check counts and visible source limitations. Missing-data and mixed outcome states are covered by automated API checks; real future outages remain possible.

The OSM fallback uses small read-only extracts, serializes requests and caches them for 24 hours. It does not promise complete mapping, venue admission or availability. Its venue-search coverage is about 1 km around the selected centre when the broader map search fails, and the result explicitly says so. It must not be described as searching the entire requested radius in that fallback case.

No weather thresholds were relaxed to force the successful example. The recording is development evidence and is never read to generate runtime answers. Neither this test nor the cache guarantees future source availability or judging-window uptime.
