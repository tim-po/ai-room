# Launch status: BLOCKED / saved only

This file is documentation, not an engine-enforced interlock. Do not press Start until the operator completes these checks; manager first turn also checks and asks_owner if they remain unmet.

- [ ] Quota/auth errors are classified and halt/park scheduling in the RUNNING engine, with regression evidence (not just prompt text).
- [ ] Attempt/completed/recovery counts are auditable; manager gets authoritative remaining budget; limit behavior is verified.
- [ ] Model passthrough enabled; Codex authentication/quota and gpt-6.1-sol availability verified without a large run.
- [ ] Saved board-mode config matches Git and board injection smoke passes.
- [ ] Current frontend SHA, isolated worktree, file ownership, state paths and rollback baseline verified.
- [ ] Owner explicitly starts this saved loop after reviewing the setup.

No engine bugfix or restart was performed when this configuration was created.
