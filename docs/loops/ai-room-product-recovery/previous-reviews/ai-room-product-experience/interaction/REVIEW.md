# Interaction baseline review 001 — needs_work

2026-10-04. Independent expert/simulated evaluation, not human usability research. Full current product brief and manager-direction-002 read. Deliverables restricted to interaction/; no repository modifications, service restart, deployment, installed-data changes or subagents. Pending checkout remains clean. This is the early baseline review; it does not accept either new visual direction or staging.

Target: `/home/claude/ai-room-pending-review`, exact SHA `bc4ba3c1f2eed39e42f611836d6990acf7b0a62d`; actual running Flask app at `http://127.0.0.1:18749`, headless Chromium `153.0.8010.12`. Disposable unique DBs `/tmp/interaction-audit/audit-*.sqlite`, fresh custom account interaction-new@example.test with zero prior preferences/work. Password generated in memory and not recorded. Ordinary synthetic seed + skill seed, graph `tree-2026-10-v1`, score rule `verified-coverage-v1`, 54 nodes. Canonical graph hash `c19c98cef4c00cce21f36c796f2c8732b7229557b56da9546d786a7308a76553`. This is not staged/pending reviewed content manifest9360018f; no forms published. Server threads exited naturally with drivers.

`evidence.json`, `followup.json`, `search-recheck.json` contain actual HTTP/status/body-size, rendered text, focus and state observations. `audit.py`, `followup.py`, `search.py` preserve drivers (followups reference /tmp original driver). Screenshots include full-page and viewport pairs for main audit. Map/preferences at 360/390/768/1440 ×900; detail/list/search/lesson/profile/return at 390×844; keyboard reduced-motion at 768×900; touch emulated in followups. 720×450 reflow approximates 1440×900 at 200%, but actual browser zoom remains unverified.

Images actually opened and visually inspected: 01/02 viewport; 03 interests 360/390/768 viewport; 04 pace viewport; 06 map 360/768 viewport and 1440 full; 07 detail,08 close,09 list,10 search,12 deep,14 lesson,15 saved,16 profile,17 return,18 offline,19 recovered viewport; 22 valid-context lesson full; 23 reflow full; 24 keyboard search. Other saved captures are supplementary, not asserted as visually reviewed.

## Blocking task findings

| ID | Result and direct evidence | Required correction |
|---|---|---|
| I01 | FAIL. Anonymous and fresh authenticated entry both render map, no welcome/value flow. Normal login lands `/`; 01/02 viewport. Fresh user sees tiny «Найти своё начало» link, no onboarding automatically. | Fresh-account welcome redirect with allowed original destination, obvious first task; complete/skip/edit states. |
| I02 | FAIL. Select coding+content, Next, refresh: returns interests and zero boxes checked. `refresh_checked:0`, 04/05. development.js only saves interests on final submit. | Server draft/step persistence after every acknowledged transition, recover on refresh/logout/new context. |
| I03 | FAIL. At 360 and 390 the first viewport shows Skip and branch options but no Next; 03 images. At 768 Next becomes visible. Onboarding has no step indicator and mobile global nav competes with task. | Compact step content + visible task footer, back/skip, step orientation; test short screen and keyboard. |
| I04 | FAIL. Finish returns generic map; return after saved practical result also shows map with unnamed tiny «Продолжить урок». Profile places unknown skills before saved artifact; 16/17. Saved data exists, but first-value/return hierarchy is missing. | Named first accessible activity and visible last work/continue with result status; preserve honest evidence. |
| I05 | FAIL. List view + Cyrillic query reload resets to map and empty query. `followup.json` and `search-recheck.json`: list false, query empty. | Preserve view/query/selection through URL/history and lesson return; synchronized disclosure state. |

These are material task failures, not optional polish. New design selection should demonstrate the corrected novice journey and return hierarchy before broad rollout.

## Verified strengths and bounded findings

- Final preference save returns 200 interests PUT + successful preferences POST redirect. Coding/content remain after logout/login and Skip; editor restores two checked choices. Branch exploration coding, review and teams does not replace interests. No lost submitted work observed.
- Real lesson form saved a nonempty synthetic result. Independent practice GET after logout/login returned the exact text and submitted status. Storage is working; meaningful feedback and automatic continuation are not thereby proved.
- Map has actual root/five branches and recursive sibling neighborhoods. At tested four widths document scrollWidth equalled viewport width. Arrows moved focus coding→teams; Enter opened details. Touch tap selected coding. Escape hid detail and restored coding node focus; mobile scroll changed 414→111 while retaining coding neighborhood. This is a useful existing orientation behavior; exact original scroll restoration across all actions is unverified.
- Map load network failure shows understandable message and Retry (18); after removing injected abort, pressing Retry loads real graph (19). This is confirmed recovery, not merely a mock success screen.
- Search focus caveat: main programmatic `fill` after selection/list yielded active element with empty id, suggesting the close-and-focus path needs scrutiny. TWO subsequent character-by-character keyboard tests, including touch-selected coding→Escape→list, retained INPUT focus and full «провер». **Do not report a confirmed inability to type/search.** Keep regression case; current confirmed defect is query/view loss on refresh.
- Search/list preserve an inner scroll offset that can show the first result partially clipped (10/24); list's selected coding section is below the fold (09). Tighten orientation/scroll restoration in redesign; do not infer inaccessible content from screenshot alone.
- Deep branch screenshot 12 shows substantial empty stage and generic detail, no visible immediate learning action. In this ordinary seed, many nodes have empty inventories. This does not establish missing reviewed content on staging.
- Lesson and saved form are readable with real task/checklist/material link and explicit unavailable tutor review. Profile unknown states are honest. A submitted artifact is not graded competence.

## HTTP checks, harness corrections and limits

All graph/me and valid node API routes triggered by reviewed map/preferences/profile views were independently reopened using browser request GET, returning 200 with nonempty JSON and real node structures; `evidence.json:get_probes` records each route and bytes. Explore POST and interests PUT succeeded with server responses. Lesson and practice GETs return 200 with real lesson/saved text. A new untouched practice GET in followup correctly returns JSON null, not missing backend.

The first driver mistakenly navigated `/skills` (actual map is `/`) and timed out. Corrected driver reran from a new account and overwrote map captures with the actual successful route; excluded from product failures. A guessed lesson context `basic-ai.instructions` caused a 404; followup used graph-discovered `basic-ai.context`, returned 200 and rendered real lesson (22). That 404 is harness error, not broken map link. `/onboarding` probe returned 404, but the required feature failure is observed login behavior rather than a mandated route spelling.

No staging network probes performed because this role's permitted HTTP probe scope is localhost. Manager's prior dae0217 health is not my staged verification. Not verified this turn: final new visual directions, approved assessment/feedback inventory, diagnostic completion, actual native 200% zoom, screen reader, expired/forbidden/logout-midstep states, every lesson/video/course/catalogue/help surface, long-absence/next-day return, all sizes for every state. These remain mandatory independent gates; no full-product pass.

## Implementation handoff

`INTERACTION-CONTRACT.md` specifies concrete navigation, onboarding state transitions, server persistence contract proposal, map/list/history/focus/touch behavior, first-viewport priorities, learning/return and error recovery, research links and retest tasks. Backend/schema changes require the shared manager ownership agreement; this document does not transfer ownership. Primary W3C disclosure/dialog guidance was browsed on 2026-10-04. Five-product research register was read, not re-labelled as my own five product study. No causal retention claims made.

Next review needs selected direction implemented at exact candidate + actual content ledger, fresh-account normal entry, interruption at each step, skip/edit, save/reopen first work and full map context sequence. Status: needs_work.
