-- Google is now the only login path. Keep legacy actors for audit foreign keys,
-- but deactivate and clear their old password hashes.
ALTER TABLE access_codes
  ALTER COLUMN code_hash DROP NOT NULL;

UPDATE access_codes
SET active = FALSE,
    code_hash = NULL
WHERE code_hash IS DISTINCT FROM 'google-only';
