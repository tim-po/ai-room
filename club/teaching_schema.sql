CREATE TABLE IF NOT EXISTS teaching_uploads (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), request_id TEXT NOT NULL,
 filename TEXT NOT NULL, media_type TEXT NOT NULL, size INTEGER NOT NULL CHECK(size>0),
 sha256 TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(owner_id,request_id)
);
CREATE TABLE IF NOT EXISTS teaching_jobs (
 id TEXT PRIMARY KEY, upload_id TEXT NOT NULL UNIQUE REFERENCES teaching_uploads(id),
 state TEXT NOT NULL CHECK(state IN ('queued','running','blocked','failed','cancelled','ready')),
 attempt INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 1,
 error_code TEXT, lease_token TEXT, lease_until INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS teaching_job_events (
 id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES teaching_jobs(id),
 state TEXT NOT NULL, attempt INTEGER NOT NULL, error_code TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS teaching_sources (
 upload_id TEXT PRIMARY KEY REFERENCES teaching_uploads(id), body TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS teaching_package_sources (
 job_id TEXT NOT NULL REFERENCES teaching_jobs(id), upload_id TEXT NOT NULL REFERENCES teaching_uploads(id),
 position INTEGER NOT NULL, PRIMARY KEY(job_id,upload_id)
);
CREATE TABLE IF NOT EXISTS teaching_transcripts (
 upload_id TEXT PRIMARY KEY REFERENCES teaching_uploads(id), body TEXT NOT NULL,
 provider TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS teaching_drafts (
 job_id TEXT NOT NULL REFERENCES teaching_jobs(id), revision INTEGER NOT NULL, body TEXT NOT NULL,
 sources TEXT NOT NULL, release_id TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
 editor_id TEXT REFERENCES users(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(job_id,revision)
);
CREATE TABLE IF NOT EXISTS teaching_publications (
 job_id TEXT PRIMARY KEY REFERENCES teaching_jobs(id), draft_revision INTEGER NOT NULL,
 lesson_id TEXT NOT NULL REFERENCES lessons(id), release_id TEXT NOT NULL REFERENCES skill_releases(id),
 reviewed_by TEXT NOT NULL REFERENCES users(id), review_note TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS teaching_drafts_immutable BEFORE UPDATE ON teaching_drafts BEGIN SELECT RAISE(ABORT,'immutable draft edition'); END;
CREATE TRIGGER IF NOT EXISTS teaching_drafts_retain BEFORE DELETE ON teaching_drafts BEGIN SELECT RAISE(ABORT,'retain draft edition'); END;
