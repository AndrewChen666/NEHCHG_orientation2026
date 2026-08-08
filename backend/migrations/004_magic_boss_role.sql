-- The magic encounter is operated by a dedicated, on-site magic boss account.
-- Keep this migration safe for both fresh databases and existing sessions.

ALTER TABLE access_codes DROP CONSTRAINT IF EXISTS access_codes_role_check;
ALTER TABLE access_codes
  ADD CONSTRAINT access_codes_role_check
  CHECK (role IN ('coordinator', 'market_master', 'team_facilitator', 'magic_boss'));

ALTER TABLE access_codes DROP CONSTRAINT IF EXISTS access_codes_check;
ALTER TABLE access_codes DROP CONSTRAINT IF EXISTS access_codes_scope_check;
ALTER TABLE access_codes
  ADD CONSTRAINT access_codes_scope_check
  CHECK ((role = 'coordinator' AND team_id IS NULL AND market_id IS NULL)
      OR (role = 'market_master' AND market_id IS NOT NULL AND team_id IS NULL)
      OR (role = 'team_facilitator' AND team_id IS NOT NULL AND market_id IS NULL)
      OR (role = 'magic_boss' AND team_id IS NULL AND market_id IS NULL));

ALTER TABLE magic_challenges ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
UPDATE magic_challenges SET idempotency_key = 'legacy-' || id::text WHERE idempotency_key IS NULL;
ALTER TABLE magic_challenges ALTER COLUMN idempotency_key SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS magic_challenges_idempotency_idx
  ON magic_challenges(session_id, idempotency_key);

CREATE INDEX IF NOT EXISTS magic_challenges_pending_idx
  ON magic_challenges(session_id, created_at)
  WHERE result IS NULL;

CREATE INDEX IF NOT EXISTS magic_challenges_history_idx
  ON magic_challenges(session_id, judged_at DESC)
  WHERE result IS NOT NULL;
