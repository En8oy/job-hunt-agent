-- Job search tracker schema (SQLite).
-- All dates/times are local Mexico City time, ISO format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  name_norm   TEXT NOT NULL UNIQUE,     -- lowercase, no accents/punctuation/legal suffixes
  website     TEXT,
  notes       TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
  id          INTEGER PRIMARY KEY,
  company_id  INTEGER REFERENCES companies(id),
  name        TEXT,
  email       TEXT UNIQUE,
  role        TEXT,                     -- recruiter, EA, founder...
  notes       TEXT
);

CREATE TABLE IF NOT EXISTS applications (
  id             INTEGER PRIMARY KEY,
  company_id     INTEGER NOT NULL REFERENCES companies(id),
  position       TEXT NOT NULL,
  position_norm  TEXT NOT NULL,
  platform       TEXT NOT NULL,         -- where it was found: LinkedIn, OCC Mundial, Torre...
  ats            TEXT,                  -- where it was submitted: Greenhouse, Ashby, Lever...
  job_url        TEXT UNIQUE,           -- NULL allowed (e.g. Computrabajo)
  status         TEXT NOT NULL DEFAULT 'applied' CHECK (status IN (
                   'applied','in_review','screening','needs_info','in_process',
                   'offer','hired','rejected','withdrawn','no_response','on_hold')),
  applied_at     TEXT,                  -- NULL if unknown (2026-09-28 backfill)
  modality       TEXT CHECK (modality IN ('remote','hybrid','onsite')),
  location       TEXT,
  seniority      TEXT CHECK (seniority IN ('junior','mid','senior','lead')),
  salary_text    TEXT,
  cv_used        TEXT CHECK (cv_used IN ('en','es')),
  fit_notes      TEXT,
  honesty_flags  TEXT,                  -- answers worth double-checking if they call
  applied_by     TEXT CHECK (applied_by IN ('agent','user')),
  import_ref     TEXT,                  -- id in an imported legacy tracker (e.g. 'xlsx:row 99')
  created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_app_company_pos ON applications(company_id, position_norm);
CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);

CREATE TABLE IF NOT EXISTS events (
  id              INTEGER PRIMARY KEY,
  application_id  INTEGER NOT NULL REFERENCES applications(id),
  occurred_at     TEXT,                 -- when it happened (email date); NULL if unknown
  recorded_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  type            TEXT NOT NULL CHECK (type IN (
                    'applied','email','message','status_change','assessment',
                    'interview','rejection','offer','duplicate','note')),
  source          TEXT,                 -- email, linkedin, torre, chat, legacy_notes...
  contact_id      INTEGER REFERENCES contacts(id),
  summary         TEXT NOT NULL,
  quote           TEXT,                 -- literal text; required for rejections
  from_status     TEXT,
  to_status       TEXT,
  CHECK (type <> 'rejection' OR quote IS NOT NULL OR source = 'legacy_notes')
);
CREATE INDEX IF NOT EXISTS idx_events_app ON events(application_id, occurred_at);

CREATE TABLE IF NOT EXISTS steps (
  id               INTEGER PRIMARY KEY,
  application_id   INTEGER NOT NULL REFERENCES applications(id),
  seq              INTEGER NOT NULL,
  name             TEXT NOT NULL,       -- what the company calls it
  type             TEXT NOT NULL CHECK (type IN (
                     'questionnaire','recruiter_screen','english','cognitive','psychometric',
                     'coding_test','take_home','technical','system_design','video_intro',
                     'hiring_manager','team_meet','founder_ceo','client','culture_fit',
                     'salary_negotiation','background_check','references','paid_trial',
                     'offer','other')),
  status           TEXT NOT NULL DEFAULT 'planned' CHECK (status IN (
                     'planned','to_schedule','scheduled','done',
                     'passed','failed','skipped','cancelled')),
  modality         TEXT CHECK (modality IN ('remote','onsite','async')),
  scheduled_at     TEXT,
  duration_min     INTEGER,
  deadline_at      TEXT,
  link             TEXT,
  result           TEXT,
  details          TEXT CHECK (details IS NULL OR json_valid(details)),
  defined_by       TEXT NOT NULL CHECK (defined_by IN ('ai','user','company')),
  source_event_id  INTEGER REFERENCES events(id),
  created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE (application_id, seq)
);

CREATE TABLE IF NOT EXISTS tasks (
  id              INTEGER PRIMARY KEY,
  application_id  INTEGER REFERENCES applications(id),
  step_id         INTEGER REFERENCES steps(id),
  owner           TEXT NOT NULL DEFAULT 'user' CHECK (owner IN ('user','agent')),
  title           TEXT NOT NULL,
  due_at          TEXT,
  link            TEXT,
  status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','expired','cancelled')),
  created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  done_at         TEXT
);

CREATE TABLE IF NOT EXISTS screening_answers (
  id              INTEGER PRIMARY KEY,
  application_id  INTEGER NOT NULL REFERENCES applications(id),
  step_id         INTEGER REFERENCES steps(id),
  question        TEXT NOT NULL,
  answer          TEXT NOT NULL,
  topic           TEXT,                 -- salary, english, years_exp, skill_level, availability, other
  honesty_note    TEXT,                 -- e.g. "no Nest.js experience, said so"
  answered_by     TEXT CHECK (answered_by IN ('agent','user')),
  answered_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS candidates (
  id              INTEGER PRIMARY KEY,
  platform        TEXT NOT NULL,
  job_url         TEXT UNIQUE,
  company         TEXT NOT NULL,
  position        TEXT NOT NULL,
  found_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  fit_score       INTEGER CHECK (fit_score BETWEEN 1 AND 5),
  fit_notes       TEXT,
  decision        TEXT NOT NULL DEFAULT 'pending' CHECK (decision IN ('pending','apply','skip','applied')),
  skip_reason     TEXT,
  claimed_by      TEXT,
  claimed_at      TEXT,
  application_id  INTEGER REFERENCES applications(id)
);

CREATE TABLE IF NOT EXISTS runs (
  id           INTEGER PRIMARY KEY,
  kind         TEXT NOT NULL CHECK (kind IN ('email_check','search','apply','keyword_sweep','migration')),
  platform     TEXT,
  started_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  finished_at  TEXT,
  summary      TEXT
);
