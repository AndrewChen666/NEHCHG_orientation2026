CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS game_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'running', 'paused', 'finished')),
  scheduled_start TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  paused_at TIMESTAMPTZ,
  accumulated_pause_ms BIGINT NOT NULL DEFAULT 0,
  current_period SMALLINT NOT NULL DEFAULT 0 CHECK (current_period BETWEEN 0 AND 4),
  manual_period_override SMALLINT CHECK (manual_period_override BETWEEN 1 AND 4),
  config JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  number SMALLINT NOT NULL CHECK (number BETWEEN 1 AND 12),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, number)
);

CREATE TABLE IF NOT EXISTS markets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  name TEXT NOT NULL,
  map_x NUMERIC(6, 3),
  map_y NUMERIC(6, 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, code)
);

CREATE TABLE IF NOT EXISTS access_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('coordinator', 'market_master', 'team_facilitator')),
  display_name TEXT NOT NULL,
  team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
  market_id UUID REFERENCES markets(id) ON DELETE CASCADE,
  code_hash TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK ((role = 'coordinator' AND team_id IS NULL AND market_id IS NULL)
      OR (role = 'market_master' AND market_id IS NOT NULL AND team_id IS NULL)
      OR (role = 'team_facilitator' AND team_id IS NOT NULL AND market_id IS NULL))
);

CREATE TABLE IF NOT EXISTS team_wallets (
  team_id UUID PRIMARY KEY REFERENCES teams(id) ON DELETE CASCADE,
  balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_inventory (
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  resource_type TEXT NOT NULL CHECK (resource_type IN ('dragon_egg', 'time_device', 'unicorn_blood', 'basilisk_fang')),
  quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (team_id, resource_type)
);

CREATE TABLE IF NOT EXISTS market_rates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
  period SMALLINT NOT NULL CHECK (period BETWEEN 1 AND 4),
  resource_type TEXT NOT NULL CHECK (resource_type IN ('dragon_egg', 'time_device', 'unicorn_blood', 'basilisk_fang')),
  buy_price INTEGER NOT NULL CHECK (buy_price >= 0),
  sell_price INTEGER NOT NULL CHECK (sell_price >= 0),
  is_public BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (market_id, period, resource_type)
);

CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
  resource_type TEXT NOT NULL CHECK (resource_type IN ('dragon_egg', 'time_device', 'unicorn_blood', 'basilisk_fang')),
  direction TEXT NOT NULL CHECK (direction IN ('buy', 'sell')),
  quantity INTEGER NOT NULL CHECK (quantity = 1),
  unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
  total_amount INTEGER NOT NULL CHECK (total_amount >= 0),
  idempotency_key TEXT NOT NULL,
  recorded_by UUID NOT NULL REFERENCES access_codes(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (session_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS money_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  amount INTEGER NOT NULL,
  reason TEXT NOT NULL,
  reference_id UUID,
  created_by UUID REFERENCES access_codes(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_challenges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  difficulty_level SMALLINT NOT NULL DEFAULT 1 CHECK (difficulty_level BETWEEN 1 AND 5),
  result TEXT CHECK (result IN ('success', 'failed')),
  note TEXT,
  cooldown_until_effective_ms BIGINT,
  idempotency_key TEXT NOT NULL,
  created_by UUID NOT NULL REFERENCES access_codes(id),
  judged_by UUID REFERENCES access_codes(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  judged_at TIMESTAMPTZ,
  UNIQUE (session_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS market_ownership (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_elapsed_ms BIGINT NOT NULL DEFAULT 0,
  ended_at TIMESTAMPTZ,
  ended_elapsed_ms BIGINT,
  rate_per_minute INTEGER NOT NULL DEFAULT 3 CHECK (rate_per_minute >= 0),
  CHECK (ended_elapsed_ms IS NULL OR ended_elapsed_ms >= started_elapsed_ms)
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_owner_per_market
  ON market_ownership(market_id) WHERE ended_at IS NULL;

CREATE TABLE IF NOT EXISTS magic_questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  difficulty_level SMALLINT NOT NULL CHECK (difficulty_level BETWEEN 1 AND 5),
  prompt TEXT NOT NULL,
  answer_note TEXT,
  reward INTEGER NOT NULL CHECK (reward IN (1, 3, 5, 10, 20)),
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS magic_challenges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  question_id UUID NOT NULL REFERENCES magic_questions(id),
  result TEXT NOT NULL CHECK (result IN ('success', 'failed')),
  reward INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  recorded_by UUID NOT NULL REFERENCES access_codes(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE magic_challenges ALTER COLUMN result DROP NOT NULL;
ALTER TABLE magic_challenges ADD COLUMN IF NOT EXISTS judged_by UUID REFERENCES access_codes(id);
ALTER TABLE magic_challenges ADD COLUMN IF NOT EXISTS judged_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS black_market_cards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  effect_type TEXT NOT NULL,
  effect_config JSONB NOT NULL DEFAULT '{}'::JSONB,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS black_market_effects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  card_id UUID NOT NULL REFERENCES black_market_cards(id),
  team_id UUID NOT NULL REFERENCES teams(id),
  status TEXT NOT NULL DEFAULT 'drawn' CHECK (status IN ('drawn', 'applied', 'voided')),
  idempotency_key TEXT NOT NULL,
  applied_by UUID REFERENCES access_codes(id),
  applied_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE black_market_effects ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
UPDATE black_market_effects SET idempotency_key = id::TEXT WHERE idempotency_key IS NULL;
ALTER TABLE black_market_effects ALTER COLUMN idempotency_key SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS black_market_effects_idempotency_idx ON black_market_effects(session_id, team_id, idempotency_key);

CREATE TABLE IF NOT EXISTS game_event_counters (
  session_id UUID PRIMARY KEY REFERENCES game_sessions(id) ON DELETE CASCADE,
  next_sequence BIGINT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS game_events (
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  sequence BIGINT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, sequence)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
  actor_id UUID REFERENCES access_codes(id),
  action TEXT NOT NULL,
  target_type TEXT,
  target_id UUID,
  payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS market_rates_market_period_idx ON market_rates(market_id, period);
CREATE INDEX IF NOT EXISTS transactions_team_created_idx ON transactions(team_id, created_at DESC);
CREATE INDEX IF NOT EXISTS game_events_session_sequence_idx ON game_events(session_id, sequence);
