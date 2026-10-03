# Private curriculum inventory

Run `python -m club.curriculum_audit --database /absolute/path/to/club.sqlite`
into a private operator file. The command opens an existing database read-only
and captures one consistent transaction. Output includes draft and member lesson
text: never place it in static assets. It contains no learner submissions or keys.

The published denominator includes every published lesson in a published course,
including synthetic fixtures. Archived/draft rows remain in the inventory with
their status. Coverage counts active mappings, not quality or demonstrated ability.
Exact duplicate body groups reveal repeated teaching text; they do not justify
mapping lessons by title. Source hashes cover objectives, teaching, practice,
checklist and media reference. Any substantive revision invalidates that pin.

For each unmapped source, review the actual text and record one of: supported
narrow outcome with paragraph citation; substantive revision required; or retained
historical source awaiting a replacement edition. A new title is not new teaching.
Keep the original lesson IDs, completion and saved work. Publish revised teaching
and mappings only as explicitly reviewed editions; historical assessment snapshots
must not be repinned to changed content. Never archive fixtures merely to improve
the reported fraction. This tool makes no mapping or curriculum decisions itself.
