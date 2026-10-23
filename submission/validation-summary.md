# v0.4 verification — Team NEXA

- 935 automated tests passed; synthetic data is confined to tests.
- 34/34 real Granite intent-extraction cases passed after generic normalization, with a fixed evaluation clock. This does not measure general base-model accuracy.
- 19/19 public HTTP API cases returned expected response contracts. All ten activities were exercised: eight recommendations, one unavailable-AQI result, one no-verified-venue result. Six missing/invalid requests asked for clarification; three unsupported/injection requests returned out-of-scope.
- Concurrent request returned HTTP 429 with Retry-After 10; browser showed a clear busy message.
- Owned API crash recovered in 3.22 seconds; owned model crash recovered in 2.41 seconds. Same public hostname remained. This is a controlled recovery test, not a future uptime guarantee.
- Desktop and 390-pixel phone layouts inspected; phone date fields use one column. No horizontal page overflow observed.
- Public model weights SHA256 verified against official IBM artifact. Actual parameter count 2,533,539,840. Public quantized from_pretrained loading generated OK.
- All six presentation slides rendered and inspected after model/team/URL updates.

Detailed response evidence: `live-upgrade-evaluation.json`; extraction: `model-upgrade-evaluation.json`; loading: `model-loading-check.json`; parameter count: `model-parameter-count.json`; the final exact-venue/sports/commute checks are in `final-live-regressions.json`.

Provider outages, incomplete maps and unseen prompts can still cause honest declines. See the root COMPLIANCE.md for each rulebook clause and the outstanding Google Form / judging-window responsibilities.

Final additional live checks: confirmed golf and cricket venues produced recommendations. The original 10 km Bharathi Park request preserved the venue/distance/duration and declined with missing AQI; the verified cycling commute returned route evidence with a decline when checks were incomplete. These outcomes are in final-live-regressions.json.

Final browser flow on the current public website returned Cubbon Park, 24 October 07:00–08:00 IST, with 20 options compared and no logged console errors. Screenshot retained with the delivered package.
