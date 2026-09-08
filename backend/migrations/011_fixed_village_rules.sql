-- 2026 活米村: fixed rules, twelve teams, and settleable market income.
-- Apply after 010_default_orientation_stages.sql.

ALTER TABLE teams DROP CONSTRAINT IF EXISTS teams_number_check;
ALTER TABLE teams
  ADD CONSTRAINT teams_number_check CHECK (number BETWEEN 1 AND 12);

ALTER TABLE market_ownership
  ADD COLUMN IF NOT EXISTS paid_minutes INTEGER NOT NULL DEFAULT 0 CHECK (paid_minutes >= 0);

-- 四次元口袋 is the sole published exception to the one-item trade rule.
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_quantity_check;
ALTER TABLE transactions
  ADD CONSTRAINT transactions_quantity_check CHECK (quantity BETWEEN 1 AND 5);

-- Preserve a coordinator-uploaded map, but make every gameplay value match
-- the published rule sheet rather than a per-session editable configuration.
UPDATE game_sessions
SET config = jsonb_build_object(
  'products', '[
    {"key":"dragon_egg","name":"龍蛋","short_name":"A","unit_name":"個"},
    {"key":"time_device","name":"時光器","short_name":"B","unit_name":"個"},
    {"key":"unicorn_blood","name":"獨角獸的血","short_name":"C","unit_name":"瓶"},
    {"key":"basilisk_fang","name":"蛇妖牙齒","short_name":"D","unit_name":"根"}
  ]'::jsonb,
  'rules', '{
    "period_count":4,"period_duration_minutes":15,"trade_quantity":1,
    "same_market_trade_block":true,"challenge_start_period":3,
    "challenge_default_difficulty":3,"challenge_occupied_difficulty":4,
    "challenge_cooldown_minutes":3,"ownership_rate_per_minute":3,
    "magic_start_period":1,"magic_reward_by_difficulty":[1,3,5,10,20],
    "black_market_start_period":2,"black_market_draw_cost":10,
    "guard_money_pouch":true,"guard_minimum_team_present":true
  }'::jsonb,
  'map', COALESCE(config->'map', '{"image_data_url":null,"width":null,"height":null}'::jsonb)
), updated_at = NOW();

-- Add the four required teams to pre-existing draft/scheduled sessions. The
-- first eight profiles are left intact so organisers do not lose their labels.
INSERT INTO teams (session_id, number, name, english_name, icon, description, tone)
SELECT s.id, n, '第 ' || n || ' 隊', 'TEAM ' || LPAD(n::text, 2, '0'), n::text,
       '等待總召設定隊名',
       (ARRAY['aurora','ignis','terra','aqua','nova','solis','ventus','luna'])[((n - 1) % 8) + 1]
FROM game_sessions s
CROSS JOIN generate_series(1, 12) AS n
WHERE s.status IN ('draft', 'scheduled')
ON CONFLICT (session_id, number) DO NOTHING;

-- A pre-game migration may safely restore fixed opening assets.
INSERT INTO team_wallets (team_id, balance)
SELECT t.id, 15
FROM teams t JOIN game_sessions s ON s.id = t.session_id
WHERE s.status IN ('draft', 'scheduled')
ON CONFLICT (team_id) DO UPDATE SET balance = EXCLUDED.balance, updated_at = NOW();

INSERT INTO team_inventory (team_id, resource_type, quantity)
SELECT t.id, resource_type, 0
FROM teams t
JOIN game_sessions s ON s.id = t.session_id
CROSS JOIN (VALUES ('dragon_egg'), ('time_device'), ('unicorn_blood'), ('basilisk_fang')) AS resources(resource_type)
WHERE s.status IN ('draft', 'scheduled')
ON CONFLICT (team_id, resource_type) DO UPDATE SET quantity = EXCLUDED.quantity, updated_at = NOW();
