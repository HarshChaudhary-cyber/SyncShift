-- =============================================================================
-- SyncShift Database Schema
-- Student / Work Schedule Conflict Assistant
-- PostgreSQL 14+ / Supabase / Neon Compatible
-- =============================================================================

-- Enable UUID extension if needed for distributed IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. ENUMS
-- -----------------------------------------------------------------------------

CREATE TYPE block_type AS ENUM ('class', 'shift');
CREATE TYPE block_status AS ENUM ('enrolled', 'tentative', 'dropped');
CREATE TYPE conflict_status AS ENUM ('unresolved', 'resolved', 'ignored');

-- -----------------------------------------------------------------------------
-- 2. USERS
-- -----------------------------------------------------------------------------

CREATE TABLE users (
  id                      BIGSERIAL PRIMARY KEY,
  name                    VARCHAR(120) NOT NULL,
  email                   VARCHAR(255) UNIQUE NOT NULL,
  password_hash           VARCHAR(255) NOT NULL,
  timezone                VARCHAR(64) NOT NULL DEFAULT 'Europe/London',
  weekly_work_hour_limit  NUMERIC(4, 1) NOT NULL DEFAULT 20.0, -- e.g. 20.0 for visa compliance
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- -----------------------------------------------------------------------------
-- 3. COURSES (Academic context & color tags)
-- -----------------------------------------------------------------------------

CREATE TABLE courses (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code        VARCHAR(32) NOT NULL,            -- e.g. "CS101", "MATH220"
  name        VARCHAR(255) NOT NULL,           -- e.g. "Data Structures"
  color       VARCHAR(32) DEFAULT '#2563eb',  -- hex or tailwind token
  term        VARCHAR(32),                     -- e.g. "Fall 2026"
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_courses_user_id ON courses(user_id);

-- -----------------------------------------------------------------------------
-- 4. TIME_BLOCKS (The core table for classes and work shifts)
-- -----------------------------------------------------------------------------

CREATE TABLE time_blocks (
  id                  BIGSERIAL PRIMARY KEY,
  user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type                block_type NOT NULL,
  status              block_status NOT NULL DEFAULT 'enrolled',
  course_id           BIGINT REFERENCES courses(id) ON DELETE SET NULL,
  title               VARCHAR(255) NOT NULL,
  location            VARCHAR(255),
  
  -- Recurrence & Timing
  is_recurring        BOOLEAN NOT NULL DEFAULT TRUE,
  specific_date       DATE,                                         -- populated ONLY when is_recurring = FALSE
  day_of_week         SMALLINT CHECK (day_of_week BETWEEN 0 AND 6), -- 0 = Sun, 1 = Mon ... 6 = Sat
  start_time          TIME NOT NULL,
  end_time            TIME NOT NULL,
  duration_minutes    INT NOT NULL CHECK (duration_minutes > 0),
  is_overnight        BOOLEAN NOT NULL DEFAULT FALSE,               -- true if end_time < start_time
  
  -- Effective Range for Recurring Series
  effective_from      DATE,                                         -- semester start
  effective_until     DATE,                                         -- semester end
  
  -- Work Shifts & Flexibility
  is_flexible         BOOLEAN DEFAULT FALSE,
  hourly_wage         NUMERIC(10, 2),                               -- optional: for earnings estimate
  is_imported         BOOLEAN NOT NULL DEFAULT FALSE,               -- true if imported from .ics
  deleted             BOOLEAN NOT NULL DEFAULT FALSE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Recurrence Integrity Constraint:
  CONSTRAINT check_recurrence_integrity CHECK (
    (is_recurring = TRUE  AND specific_date IS NULL) OR
    (is_recurring = FALSE AND specific_date IS NOT NULL)
  )
);

CREATE INDEX idx_time_blocks_user_dow ON time_blocks(user_id, day_of_week) WHERE deleted = FALSE;
CREATE INDEX idx_time_blocks_active ON time_blocks(user_id, status) WHERE deleted = FALSE;
CREATE INDEX idx_time_blocks_specific_date ON time_blocks(user_id, specific_date) WHERE is_recurring = FALSE AND deleted = FALSE;

-- -----------------------------------------------------------------------------
-- 5. BLOCK_OVERRIDES (Single-week drag exceptions / shift swaps)
-- -----------------------------------------------------------------------------

CREATE TABLE block_overrides (
  id                  BIGSERIAL PRIMARY KEY,
  time_block_id       BIGINT NOT NULL REFERENCES time_blocks(id) ON DELETE CASCADE,
  user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  original_date       DATE NOT NULL,          -- which specific occurrence is being overridden
  override_date       DATE,                   -- new date (NULL if shift was cancelled this week)
  start_time          TIME,                   -- new start time (defaults to block start if NULL)
  duration_minutes    INT,                    -- new duration (defaults to block duration if NULL)
  is_cancelled        BOOLEAN DEFAULT FALSE,  -- true if student took off this week
  note                VARCHAR(255),           -- e.g. "Swapped with Alex"
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (time_block_id, original_date)
);

CREATE INDEX idx_overrides_lookup ON block_overrides(user_id, override_date);

-- -----------------------------------------------------------------------------
-- 6. CONFLICTS (Persisted log / cache of detected time-block collisions)
-- -----------------------------------------------------------------------------

CREATE TABLE conflicts (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  block_a_id      BIGINT NOT NULL REFERENCES time_blocks(id) ON DELETE CASCADE,
  block_b_id      BIGINT NOT NULL REFERENCES time_blocks(id) ON DELETE CASCADE,
  week_starting   DATE NOT NULL,
  overlap_minutes INT NOT NULL,
  status          conflict_status NOT NULL DEFAULT 'unresolved',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (block_a_id, block_b_id, week_starting)
);

CREATE INDEX idx_conflicts_user_unresolved ON conflicts(user_id, status) WHERE status = 'unresolved';

-- -----------------------------------------------------------------------------
-- 7. USEFUL VIEWS
-- -----------------------------------------------------------------------------

-- View: Weekly active shift hours per user (Visa compliance engine)
CREATE OR REPLACE VIEW v_weekly_shift_hours AS
SELECT 
  u.id AS user_id,
  u.weekly_work_hour_limit,
  ROUND(COALESCE(SUM(tb.duration_minutes), 0) / 60.0, 2) AS committed_shift_hours,
  (ROUND(COALESCE(SUM(tb.duration_minutes), 0) / 60.0, 2) > u.weekly_work_hour_limit) AS exceeds_visa_limit
FROM users u
LEFT JOIN time_blocks tb ON tb.user_id = u.id 
  AND tb.type = 'shift' 
  AND tb.status = 'enrolled'
  AND tb.deleted = FALSE
GROUP BY u.id, u.weekly_work_hour_limit;

-- -----------------------------------------------------------------------------
-- 8. NOTIFICATIONS & REMINDERS
-- -----------------------------------------------------------------------------

CREATE TABLE push_subscriptions (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  endpoint    TEXT UNIQUE NOT NULL,
  p256dh      TEXT NOT NULL,
  auth        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_push_subs_user_id ON push_subscriptions(user_id);

CREATE TABLE notification_prefs (
  user_id             BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  push_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
  email_enabled       BOOLEAN NOT NULL DEFAULT FALSE,
  class_reminder_min  INT NOT NULL DEFAULT 30,
  shift_reminder_min  INT NOT NULL DEFAULT 60,
  study_reminder_min  INT NOT NULL DEFAULT 15,
  deadline_reminder   BOOLEAN NOT NULL DEFAULT TRUE,
  conflict_alerts     BOOLEAN NOT NULL DEFAULT TRUE,
  quiet_hours_start   TIME,
  quiet_hours_end     TIME
);

CREATE TABLE notification_log (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type        VARCHAR(50) NOT NULL, -- 'class', 'shift', 'study', 'deadline', 'conflict', 'test'
  title       VARCHAR(255) NOT NULL,
  body        VARCHAR(500) NOT NULL,
  sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  channel     VARCHAR(20) NOT NULL, -- 'push' | 'email'
  dedup_key   VARCHAR(255)
);

CREATE INDEX idx_notification_log_user_sent ON notification_log(user_id, sent_at DESC);
CREATE INDEX idx_notification_log_dedup ON notification_log(dedup_key);

