-- Give existing orientation sessions the same three-stage starting flow as new sessions.
-- Sessions that already have more than one configured stage are left untouched.

DO $$
DECLARE
  legacy_session RECORD;
BEGIN
  FOR legacy_session IN
    SELECT s.id AS session_id, v.id AS village_id
    FROM game_sessions s
    JOIN activity_stages v ON v.session_id = s.id
    WHERE v.stage_type = 'magic_village'
      AND v.sort_order = 1
      AND (SELECT COUNT(*) FROM activity_stages a WHERE a.session_id = s.id) = 1
  LOOP
    -- Move the legacy row out of the way while the unique sort-order index exists.
    UPDATE activity_stages
    SET sort_order = 1000000,
        updated_at = NOW()
    WHERE id = legacy_session.village_id;

    INSERT INTO activity_stages (
      session_id, name, stage_type, sort_order, start_offset_ms,
      duration_minutes, config, personal_multiplier, team_multiplier, college_multiplier
    )
    VALUES (
      legacy_session.session_id, '破冰', 'icebreaker', 1, 0,
      30, '{}'::jsonb, 1, 1, 1
    );

    INSERT INTO activity_stages (
      session_id, name, stage_type, sort_order, start_offset_ms,
      duration_minutes, config, personal_multiplier, team_multiplier, college_multiplier
    )
    VALUES (
      legacy_session.session_id, '純計分', 'score_only', 2, 30 * 60 * 1000,
      45, '{}'::jsonb, 1, 1, 1
    );

    UPDATE activity_stages
    SET sort_order = 3,
        start_offset_ms = 75 * 60 * 1000,
        updated_at = NOW()
    WHERE id = legacy_session.village_id;
  END LOOP;
END $$;

-- Keep the coordinator able to enter every default stage after the migration.
INSERT INTO stage_role_assignments (session_id, stage_id, participant_id, role, scope_type)
SELECT a.session_id, a.id, p.id, 'coordinator', 'session'
FROM activity_stages a
JOIN participants p
  ON p.session_id = a.session_id
 AND p.participant_no = 'COORDINATOR'
WHERE a.sort_order IN (1, 2)
ON CONFLICT (stage_id, participant_id, role, scope_type, scope_id) DO NOTHING;
