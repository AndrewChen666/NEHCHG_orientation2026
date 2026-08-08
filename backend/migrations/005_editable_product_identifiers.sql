-- Product identifiers are configured per session. Runtime validation uses game_sessions.config.
ALTER TABLE team_inventory DROP CONSTRAINT IF EXISTS team_inventory_resource_type_check;
ALTER TABLE market_rates DROP CONSTRAINT IF EXISTS market_rates_resource_type_check;
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_resource_type_check;
