CREATE TABLE IF NOT EXISTS skill_releases (
 id TEXT PRIMARY KEY, body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skill_active (singleton INTEGER PRIMARY KEY CHECK(singleton=1), release_id TEXT NOT NULL REFERENCES skill_releases(id));
CREATE TABLE IF NOT EXISTS skill_interests (user_id TEXT REFERENCES users(id), node_id TEXT NOT NULL, PRIMARY KEY(user_id,node_id));
CREATE TABLE IF NOT EXISTS skill_explorations (user_id TEXT REFERENCES users(id), node_id TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,node_id));
CREATE TABLE IF NOT EXISTS skill_forms (
 id TEXT PRIMARY KEY, release_id TEXT NOT NULL REFERENCES skill_releases(id), node_id TEXT NOT NULL,
 body TEXT NOT NULL, access TEXT NOT NULL CHECK(access IN ('free','member')), reviewed_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skill_attempts (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), form_id TEXT NOT NULL REFERENCES skill_forms(id),
 request_id TEXT NOT NULL, mode TEXT NOT NULL CHECK(mode IN ('certification','practice')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id,request_id)
);
CREATE TABLE IF NOT EXISTS skill_results (
 attempt_id TEXT PRIMARY KEY REFERENCES skill_attempts(id), answers TEXT NOT NULL, body TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skill_evidence (
 user_id TEXT NOT NULL REFERENCES users(id), release_id TEXT NOT NULL REFERENCES skill_releases(id),
 objective_id TEXT NOT NULL, objective_revision INTEGER NOT NULL, attempt_id TEXT NOT NULL REFERENCES skill_attempts(id),
 kind TEXT NOT NULL CHECK(kind='understanding'), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id,objective_id,objective_revision,kind)
);
CREATE TRIGGER IF NOT EXISTS skill_forms_immutable BEFORE UPDATE ON skill_forms BEGIN SELECT RAISE(ABORT,'immutable form'); END;
CREATE TRIGGER IF NOT EXISTS skill_releases_immutable BEFORE UPDATE ON skill_releases BEGIN SELECT RAISE(ABORT,'immutable release'); END;
CREATE TRIGGER IF NOT EXISTS skill_results_immutable BEFORE UPDATE ON skill_results BEGIN SELECT RAISE(ABORT,'immutable result'); END;
CREATE TRIGGER IF NOT EXISTS skill_evidence_immutable BEFORE UPDATE ON skill_evidence BEGIN SELECT RAISE(ABORT,'immutable evidence'); END;
CREATE TRIGGER IF NOT EXISTS skill_attempts_immutable BEFORE UPDATE ON skill_attempts BEGIN SELECT RAISE(ABORT,'immutable attempt'); END;
CREATE TRIGGER IF NOT EXISTS skill_forms_no_delete BEFORE DELETE ON skill_forms BEGIN SELECT RAISE(ABORT,'retain historical form'); END;
CREATE TRIGGER IF NOT EXISTS skill_releases_no_delete BEFORE DELETE ON skill_releases BEGIN SELECT RAISE(ABORT,'retain historical release'); END;
CREATE TRIGGER IF NOT EXISTS skill_attempts_no_delete BEFORE DELETE ON skill_attempts BEGIN SELECT RAISE(ABORT,'retain historical attempt'); END;
CREATE TRIGGER IF NOT EXISTS skill_results_no_delete BEFORE DELETE ON skill_results BEGIN SELECT RAISE(ABORT,'retain historical result'); END;
CREATE TRIGGER IF NOT EXISTS skill_evidence_no_delete BEFORE DELETE ON skill_evidence BEGIN SELECT RAISE(ABORT,'retain historical evidence'); END;

CREATE TABLE IF NOT EXISTS skill_diagnostics (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), request_id TEXT NOT NULL,
 release_id TEXT NOT NULL REFERENCES skill_releases(id), body TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active','skipped')),
 revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(user_id,request_id)
);

CREATE TABLE IF NOT EXISTS skill_practical_tasks (
 id TEXT PRIMARY KEY, form_id TEXT NOT NULL REFERENCES skill_forms(id),
 objective_id TEXT NOT NULL, objective_revision INTEGER NOT NULL,
 body TEXT NOT NULL, reviewed_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skill_practical_submissions (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), task_id TEXT NOT NULL REFERENCES skill_practical_tasks(id),
 request_id TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
 state TEXT NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','submitted')),
 revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(user_id,request_id)
);
CREATE TABLE IF NOT EXISTS skill_practical_decisions (
 submission_id TEXT PRIMARY KEY REFERENCES skill_practical_submissions(id),
 reviewer_id TEXT NOT NULL REFERENCES users(id), body TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skill_application_evidence (
 user_id TEXT NOT NULL REFERENCES users(id), objective_id TEXT NOT NULL, objective_revision INTEGER NOT NULL,
 submission_id TEXT NOT NULL REFERENCES skill_practical_decisions(submission_id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id,objective_id,objective_revision)
);
CREATE TRIGGER IF NOT EXISTS practical_tasks_immutable BEFORE UPDATE ON skill_practical_tasks BEGIN SELECT RAISE(ABORT,'immutable practical rubric'); END;
CREATE TRIGGER IF NOT EXISTS practical_tasks_retain BEFORE DELETE ON skill_practical_tasks BEGIN SELECT RAISE(ABORT,'retain practical rubric'); END;
CREATE TRIGGER IF NOT EXISTS practical_submissions_frozen BEFORE UPDATE ON skill_practical_submissions WHEN OLD.state='submitted' BEGIN SELECT RAISE(ABORT,'submitted work is frozen'); END;
CREATE TRIGGER IF NOT EXISTS practical_submissions_retain BEFORE DELETE ON skill_practical_submissions BEGIN SELECT RAISE(ABORT,'retain practical submission'); END;
CREATE TRIGGER IF NOT EXISTS practical_decisions_immutable BEFORE UPDATE ON skill_practical_decisions BEGIN SELECT RAISE(ABORT,'immutable practical decision'); END;
CREATE TRIGGER IF NOT EXISTS practical_decisions_retain BEFORE DELETE ON skill_practical_decisions BEGIN SELECT RAISE(ABORT,'retain practical decision'); END;
CREATE TRIGGER IF NOT EXISTS application_evidence_immutable BEFORE UPDATE ON skill_application_evidence BEGIN SELECT RAISE(ABORT,'immutable application evidence'); END;
CREATE TRIGGER IF NOT EXISTS application_evidence_retain BEFORE DELETE ON skill_application_evidence BEGIN SELECT RAISE(ABORT,'retain application evidence'); END;

CREATE TABLE IF NOT EXISTS skill_graph_proposals (
 id TEXT PRIMARY KEY, base_release TEXT NOT NULL REFERENCES skill_releases(id), source TEXT NOT NULL,
 created_by TEXT NOT NULL REFERENCES users(id), revision INTEGER NOT NULL DEFAULT 1,
 state TEXT NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','active','rejected','rolled_back')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skill_graph_editions (
 proposal_id TEXT NOT NULL REFERENCES skill_graph_proposals(id), revision INTEGER NOT NULL,
 body TEXT NOT NULL, note TEXT NOT NULL, editor_id TEXT NOT NULL REFERENCES users(id),
 PRIMARY KEY(proposal_id,revision)
);
CREATE TABLE IF NOT EXISTS skill_graph_events (
 id INTEGER PRIMARY KEY, proposal_id TEXT NOT NULL REFERENCES skill_graph_proposals(id), revision INTEGER NOT NULL,
 action TEXT NOT NULL CHECK(action IN ('activate','reject','rollback')), actor_id TEXT NOT NULL REFERENCES users(id),
 note TEXT NOT NULL, from_release TEXT NOT NULL REFERENCES skill_releases(id), to_release TEXT NOT NULL REFERENCES skill_releases(id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS graph_editions_immutable BEFORE UPDATE ON skill_graph_editions BEGIN SELECT RAISE(ABORT,'immutable graph proposal edition'); END;
CREATE TRIGGER IF NOT EXISTS graph_editions_retain BEFORE DELETE ON skill_graph_editions BEGIN SELECT RAISE(ABORT,'retain graph proposal edition'); END;
CREATE TRIGGER IF NOT EXISTS graph_events_immutable BEFORE UPDATE ON skill_graph_events BEGIN SELECT RAISE(ABORT,'immutable graph review event'); END;
CREATE TRIGGER IF NOT EXISTS graph_events_retain BEFORE DELETE ON skill_graph_events BEGIN SELECT RAISE(ABORT,'retain graph review event'); END;

-- Withdrawal never mutates published forms, past results or earned evidence.
CREATE TABLE IF NOT EXISTS skill_form_withdrawals (
 form_id TEXT PRIMARY KEY REFERENCES skill_forms(id),
 replacement_id TEXT REFERENCES skill_forms(id), reason TEXT NOT NULL,
 reviewer_id TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CHECK(replacement_id IS NULL OR replacement_id <> form_id)
);
CREATE TRIGGER IF NOT EXISTS form_withdrawals_immutable BEFORE UPDATE ON skill_form_withdrawals BEGIN SELECT RAISE(ABORT,'immutable form withdrawal'); END;
CREATE TRIGGER IF NOT EXISTS form_withdrawals_retain BEFORE DELETE ON skill_form_withdrawals BEGIN SELECT RAISE(ABORT,'retain form withdrawal'); END;

-- An explicitly reviewed release can use an unchanged form without cloning it.
CREATE TABLE IF NOT EXISTS skill_form_bindings (
 release_id TEXT NOT NULL REFERENCES skill_releases(id),
 form_id TEXT NOT NULL REFERENCES skill_forms(id),
 from_release TEXT NOT NULL REFERENCES skill_releases(id),
 reviewed_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(release_id,form_id)
);
CREATE TRIGGER IF NOT EXISTS form_bindings_immutable BEFORE UPDATE ON skill_form_bindings BEGIN SELECT RAISE(ABORT,'immutable release binding'); END;
CREATE TRIGGER IF NOT EXISTS form_bindings_retain BEFORE DELETE ON skill_form_bindings BEGIN SELECT RAISE(ABORT,'retain release binding'); END;
