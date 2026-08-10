-- Orientation 2026: Google identities, configurable activity stages,
-- stage-scoped roles, icebreaker history, and append-only scoring.

CREATE TABLE IF NOT EXISTS colleges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, code)
);

CREATE TABLE IF NOT EXISTS participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  participant_no TEXT NOT NULL,
  display_name TEXT NOT NULL,
  email TEXT NOT NULL,
  google_subject TEXT,
  college_id UUID REFERENCES colleges(id) ON DELETE SET NULL,
  team_id UUID REFERENCES teams(id) ON DELETE SET NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, participant_no)
);

CREATE UNIQUE INDEX IF NOT EXISTS participants_session_email_idx
  ON participants(session_id, LOWER(email));

CREATE UNIQUE INDEX IF NOT EXISTS participants_session_google_subject_idx
  ON participants(session_id, google_subject)
  WHERE google_subject IS NOT NULL;

CREATE TABLE IF NOT EXISTS activity_stages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  stage_type TEXT NOT NULL CHECK (stage_type IN ('icebreaker', 'score_only', 'mini_game', 'magic_village', 'custom')),
  sort_order INTEGER NOT NULL CHECK (sort_order >= 1),
  start_offset_ms BIGINT NOT NULL DEFAULT 0 CHECK (start_offset_ms >= 0),
  duration_minutes INTEGER NOT NULL CHECK (duration_minutes >= 1),
  config JSONB NOT NULL DEFAULT '{}'::JSONB,
  personal_multiplier NUMERIC(12, 4) NOT NULL DEFAULT 1 CHECK (personal_multiplier >= 0),
  team_multiplier NUMERIC(12, 4) NOT NULL DEFAULT 1 CHECK (team_multiplier >= 0),
  college_multiplier NUMERIC(12, 4) NOT NULL DEFAULT 1 CHECK (college_multiplier >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, sort_order)
);

ALTER TABLE game_sessions
  ADD COLUMN IF NOT EXISTS manual_stage_id UUID REFERENCES activity_stages(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS activity_stages_session_order_idx
  ON activity_stages(session_id, sort_order);

CREATE TABLE IF NOT EXISTS stage_role_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  stage_id UUID NOT NULL REFERENCES activity_stages(id) ON DELETE CASCADE,
  participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('coordinator', 'participant', 'team_facilitator', 'icebreaker_facilitator', 'score_keeper', 'market_master', 'magic_boss')),
  scope_type TEXT NOT NULL DEFAULT 'session' CHECK (scope_type IN ('session', 'college', 'team', 'market')),
  scope_id UUID,
  college_id UUID REFERENCES colleges(id) ON DELETE CASCADE,
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  market_id UUID REFERENCES markets(id) ON DELETE CASCADE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (stage_id, participant_id, role, scope_type, scope_id)
);

CREATE INDEX IF NOT EXISTS stage_role_assignments_lookup_idx
  ON stage_role_assignments(session_id, stage_id, participant_id, active);

ALTER TABLE access_codes
  ADD COLUMN IF NOT EXISTS participant_id UUID REFERENCES participants(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS stage_id UUID REFERENCES activity_stages(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS role_assignment_id UUID REFERENCES stage_role_assignments(id) ON DELETE SET NULL;

ALTER TABLE access_codes DROP CONSTRAINT IF EXISTS access_codes_role_check;
ALTER TABLE access_codes
  ADD CONSTRAINT access_codes_role_check
  CHECK (role IN ('coordinator', 'participant', 'team_facilitator', 'icebreaker_facilitator', 'score_keeper', 'market_master', 'magic_boss'));

ALTER TABLE access_codes DROP CONSTRAINT IF EXISTS access_codes_scope_check;

CREATE INDEX IF NOT EXISTS access_codes_participant_stage_idx
  ON access_codes(session_id, participant_id, stage_id, active);

CREATE TABLE IF NOT EXISTS icebreaker_rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  stage_id UUID NOT NULL REFERENCES activity_stages(id) ON DELETE CASCADE,
  round_number INTEGER NOT NULL CHECK (round_number >= 1),
  name TEXT NOT NULL DEFAULT '',
  created_by UUID REFERENCES access_codes(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (stage_id, round_number)
);

CREATE TABLE IF NOT EXISTS icebreaker_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  round_id UUID NOT NULL REFERENCES icebreaker_rounds(id) ON DELETE CASCADE,
  group_number INTEGER NOT NULL CHECK (group_number >= 1),
  created_by UUID REFERENCES access_codes(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (round_id, group_number)
);

CREATE TABLE IF NOT EXISTS icebreaker_group_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  round_id UUID NOT NULL REFERENCES icebreaker_rounds(id) ON DELETE CASCADE,
  group_id UUID NOT NULL REFERENCES icebreaker_groups(id) ON DELETE CASCADE,
  participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (round_id, participant_id),
  UNIQUE (group_id, participant_id)
);

CREATE INDEX IF NOT EXISTS icebreaker_group_members_history_idx
  ON icebreaker_group_members(session_id, participant_id, round_id);

CREATE TABLE IF NOT EXISTS score_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  stage_id UUID NOT NULL REFERENCES activity_stages(id) ON DELETE CASCADE,
  target_type TEXT NOT NULL CHECK (target_type IN ('personal', 'team', 'college')),
  target_id UUID NOT NULL,
  points NUMERIC(12, 2) NOT NULL,
  note TEXT,
  idempotency_key TEXT NOT NULL,
  recorded_by UUID REFERENCES access_codes(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS score_events_stage_target_idx
  ON score_events(stage_id, target_type, target_id, created_at);

CREATE INDEX IF NOT EXISTS score_events_session_created_idx
  ON score_events(session_id, created_at DESC);

-- Existing sessions keep the original village rules while gaining a stage
-- wrapper. New sessions can replace this with their own configured timeline.
INSERT INTO activity_stages (session_id, name, stage_type, sort_order, start_offset_ms, duration_minutes, config)
SELECT s.id,
       '活米村',
       'magic_village',
       1,
       0,
       GREATEST(1, COALESCE((s.config->'rules'->>'period_count')::INTEGER, 4) * COALESCE((s.config->'rules'->>'period_duration_minutes')::INTEGER, 15)),
       jsonb_build_object('legacy_period_count', COALESCE((s.config->'rules'->>'period_count')::INTEGER, 4))
FROM game_sessions s
WHERE NOT EXISTS (SELECT 1 FROM activity_stages a WHERE a.session_id = s.id);
