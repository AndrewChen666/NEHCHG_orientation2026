-- Market masters record real-world transactions and explicitly apply occupation.
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_quantity_check;
ALTER TABLE transactions ADD CONSTRAINT transactions_quantity_check CHECK (quantity >= 1);

ALTER TABLE market_challenges
  ADD COLUMN IF NOT EXISTS ownership_applied_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS ownership_applied_by UUID REFERENCES access_codes(id);

CREATE INDEX IF NOT EXISTS market_challenges_ownership_pending_idx
  ON market_challenges(market_id, result, ownership_applied_at);
