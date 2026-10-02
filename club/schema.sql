PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'learner' CHECK(role IN ('learner','editor','admin')),
 entitlement TEXT NOT NULL DEFAULT 'free' CHECK(entitlement IN ('free','member','revoked','expired')),
 goal TEXT NOT NULL DEFAULT 'essentials', experience TEXT NOT NULL DEFAULT 'beginner',
 weekly_goal INTEGER NOT NULL DEFAULT 2, onboarding_done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS courses (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, outcome TEXT NOT NULL,
 goal TEXT NOT NULL, level TEXT NOT NULL, tools TEXT NOT NULL, prerequisites TEXT NOT NULL,
 author TEXT NOT NULL, updated_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft'
 CHECK(status IN ('draft','published','archived'))
);
CREATE TABLE IF NOT EXISTS modules (
 id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses(id), title TEXT NOT NULL, position INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS lessons (
 id TEXT PRIMARY KEY, module_id TEXT NOT NULL REFERENCES modules(id), title TEXT NOT NULL,
 objective TEXT NOT NULL, body TEXT NOT NULL, minutes INTEGER NOT NULL CHECK(minutes>0),
 position INTEGER NOT NULL, access TEXT NOT NULL CHECK(access IN ('free','member')),
 video TEXT, prompt TEXT, task TEXT, checklist TEXT, status TEXT NOT NULL DEFAULT 'published'
 CHECK(status IN ('draft','published','archived'))
);
CREATE TABLE IF NOT EXISTS progress (
 user_id TEXT NOT NULL REFERENCES users(id), lesson_id TEXT NOT NULL REFERENCES lessons(id),
 completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)), video_seconds REAL NOT NULL DEFAULT 0,
 started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(user_id,lesson_id)
);
CREATE TABLE IF NOT EXISTS practice (
 user_id TEXT NOT NULL REFERENCES users(id), lesson_id TEXT NOT NULL REFERENCES lessons(id),
 body TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('draft','submitted')),
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,lesson_id)
);
CREATE TABLE IF NOT EXISTS favourites (
 user_id TEXT NOT NULL REFERENCES users(id), course_id TEXT NOT NULL REFERENCES courses(id),
 PRIMARY KEY(user_id,course_id)
);
CREATE TABLE IF NOT EXISTS help_requests (
 id INTEGER PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), lesson_id TEXT REFERENCES lessons(id),
 body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL,
 lesson_id TEXT REFERENCES lessons(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_first_lesson_event
ON events(user_id,lesson_id,name) WHERE name IN ('lesson_started','lesson_completed');
CREATE TABLE IF NOT EXISTS login_attempts (
 identity TEXT PRIMARY KEY, failures INTEGER NOT NULL, window_start INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS resources (
 id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(id),
 title TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('text','link')), content TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('published','archived'))
);
CREATE TABLE IF NOT EXISTS course_starts (
 user_id TEXT NOT NULL REFERENCES users(id), course_id TEXT NOT NULL REFERENCES courses(id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,course_id)
);
CREATE TABLE IF NOT EXISTS learning_days (
 user_id TEXT NOT NULL REFERENCES users(id), day TEXT NOT NULL,
 PRIMARY KEY(user_id,day)
);
CREATE TABLE IF NOT EXISTS lesson_visits (
 user_id TEXT NOT NULL REFERENCES users(id), lesson_id TEXT NOT NULL REFERENCES lessons(id),
 visit_order INTEGER NOT NULL, PRIMARY KEY(user_id,lesson_id)
);
-- Preserve the earliest event if concurrent submissions in an older version
-- recorded the same learner's onboarding more than once.
DELETE FROM events WHERE name='onboarding_completed' AND id NOT IN (
 SELECT MIN(id) FROM events WHERE name='onboarding_completed' GROUP BY user_id
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_onboarding_completion
ON events(user_id) WHERE name='onboarding_completed';
CREATE TABLE IF NOT EXISTS learning_routes (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, goal TEXT NOT NULL, outcome TEXT NOT NULL,
 explanation TEXT NOT NULL, owner TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft'
 CHECK(status IN ('draft','published','archived')), revision INTEGER NOT NULL DEFAULT 1,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS route_steps (
 route_id TEXT NOT NULL REFERENCES learning_routes(id), lesson_id TEXT NOT NULL REFERENCES lessons(id),
 position INTEGER NOT NULL, beginner_only INTEGER NOT NULL DEFAULT 0 CHECK(beginner_only IN (0,1)),
 PRIMARY KEY(route_id,lesson_id)
);
CREATE TABLE IF NOT EXISTS route_selections (
 user_id TEXT PRIMARY KEY REFERENCES users(id), route_id TEXT NOT NULL REFERENCES learning_routes(id),
 visit_floor INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS materials (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, outcome TEXT NOT NULL,
 format TEXT NOT NULL CHECK(format IN ('guide','use_case','workshop')),
 goal TEXT NOT NULL, level TEXT NOT NULL, tools TEXT NOT NULL, prerequisites TEXT NOT NULL,
 author TEXT NOT NULL, minutes INTEGER NOT NULL CHECK(minutes>0), body TEXT NOT NULL,
 prompt TEXT, video TEXT, access TEXT NOT NULL CHECK(access IN ('free','member')),
 status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','archived')),
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS material_resources (
 id TEXT PRIMARY KEY, material_id TEXT NOT NULL REFERENCES materials(id), title TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('text','link')), content TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('published','archived'))
);
CREATE TABLE IF NOT EXISTS material_favourites (
 user_id TEXT NOT NULL REFERENCES users(id), material_id TEXT NOT NULL REFERENCES materials(id),
 PRIMARY KEY(user_id,material_id)
);
CREATE TABLE IF NOT EXISTS material_video_positions (
 user_id TEXT NOT NULL REFERENCES users(id), material_id TEXT NOT NULL REFERENCES materials(id),
 seconds REAL NOT NULL DEFAULT 0 CHECK(seconds>=0), PRIMARY KEY(user_id,material_id)
);
PRAGMA user_version = 6;
