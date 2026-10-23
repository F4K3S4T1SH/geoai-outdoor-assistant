# Exercise distance / exact venue repair

Verified 23 October 2026 IST, version 0.3.0.

- 86 automated checks pass. New regressions cover exercise distance versus search radius, singular/plural km, explicit versus nearby venues, pace versus duration, exact-place preservation, alternate times at one venue, travel-direction labelling, an unavailable exact venue, OSM identity validation, and conflicting commute/distance goals.
- A real public HTTPS request matching “10 kms Run in Bharathi Park, puducherry” returned `clarification_needed`, field `duration`, when neither expected duration nor pace was supplied.
- Supplying 6 minutes/km and a 09:00–13:00 IST comparison window produced a 60-minute assessment, exactly one venue (Bharathi Park), four time windows, a null applied search radius and zero travel routes. Forecast concerns remained visible; conditions were not relaxed. Both real API requests together completed in 21.94 seconds from the hosting laptop. This is not an independent uptime or latency guarantee.
- `exact-venue-live-example.json` records the request and response and is never used for runtime answers.
- Browser testing confirmed that the missing-duration question opens the preferences, the expected-pace input can complete the request, and the selected mapped identity is retained.

This repair does not create a measured 10 km running course. The response and interface explicitly mark the exercise course unverified. Venue access, lap length, path continuity and capacity for the requested training distance are not established by the weather assessment. Travel-to-venue estimates are separate transport directions, not exercise-route measurements.
