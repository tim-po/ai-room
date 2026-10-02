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
