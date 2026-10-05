# Text recovery pauses playback

Candidate 548e724cc954e8efdeb73cc4cc1a14aa3d615edf; base a974350e88fcc82a6aba28370d5b4e35e2951f25. Learner-owned `club/static/lesson-context.js` now pauses the video when the learner chooses the reading fallback. This prevents audio continuing behind text and retains the existing focus/scroll transition. No backend, schema, content, shared player or deployment changes.

Actual headless Chromium 153.0.8010.12: 28 checks pass at 360×640, 390×844, 768×900 and 1440×900, with no page errors. New checks choose text during actual synthetic fixture playback after a controlled waiting timeout: playback is paused, the reading heading receives focus and the unsaved practice remains intact. Existing failed-request, retry, resume, initial-load, stalled-playback, pause and ended regressions pass. Opened text-recovery-390-viewport.png: Cyrillic wraps and reading heading focus is visible. Synthetic teaching/media and controlled events establish UI behavior only; builder expert simulation is not independent acceptance. Exact local URL, graph/content digests and checks are in evidence.json. Screenshot gallery retained. Diff whitespace check passes. Initial shell used unavailable unqualified python; corrected to python3 before editing or running verification.

Public health remains dae021716ac92abe5fdf1253093f82ac8f3f3286, schema 6. No staging deployment or production activity.

Overall work_remaining: exact-candidate independent review; approved novice activity/comparison feedback; backend substantive-return event contract; full access/native-zoom/accessibility matrix; reviewed staging deployment and same-build recheck. This bounded correction does not close those product gates.
