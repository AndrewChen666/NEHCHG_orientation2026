import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.activity import effective_elapsed_ms, stage_is_current
from app.config import Settings
from app.dependencies import get_auth_context
from app.routers.auth import _verify_google_credential
from app.routers.orientation import RoleAssignmentInput, ScoreEventRequest, StageBatchRequest
from app.security import AuthContext, create_session_token, decode_session_token


class ActivityRulesTest(TestCase):
    def test_effective_elapsed_excludes_accumulated_pause(self):
        started = datetime(2026, 1, 1, tzinfo=timezone.utc)
        row = {"started_at": started, "paused_at": started + timedelta(seconds=30), "accumulated_pause_ms": 5000}
        self.assertEqual(effective_elapsed_ms(row), 25_000)

    def test_stage_batch_rejects_duplicate_order(self):
        stage = {"name": "破冰", "stage_type": "icebreaker", "sort_order": 1, "duration_minutes": 30}
        with self.assertRaises(ValueError):
            StageBatchRequest(stages=[stage, {**stage, "name": "計分"}])

    def test_zero_multiplier_is_valid(self):
        batch = StageBatchRequest(stages=[{"name": "活米村", "stage_type": "magic_village", "sort_order": 1, "duration_minutes": 60, "personal_multiplier": 0}])
        self.assertEqual(batch.stages[0].personal_multiplier, 0)

    def test_role_scope_requires_matching_target(self):
        with self.assertRaises(ValueError):
            RoleAssignmentInput(stage_id=uuid4(), participant_id=uuid4(), role="team_facilitator", scope_type="team")

    def test_score_event_accepts_decimal_points_and_idempotency_key(self):
        event = ScoreEventRequest(target_type="personal", target_id=uuid4(), points=Decimal("12.50"), idempotency_key="round-1-person-1")
        self.assertEqual(event.points, Decimal("12.50"))

    def test_stage_is_current(self):
        current = {"id": uuid4()}
        self.assertTrue(stage_is_current(current, current))
        self.assertFalse(stage_is_current({"id": uuid4()}, current))


class GoogleIdentityTest(TestCase):
    def setUp(self):
        self.settings = Settings(google_client_id="orientation-client.apps.googleusercontent.com")

    @patch("app.routers.auth.id_token.verify_oauth2_token")
    def test_google_claims_are_accepted_when_verified(self, verify):
        claims = {"iss": "https://accounts.google.com", "email_verified": True, "sub": "google-sub", "email": "person@example.com"}
        verify.return_value = claims
        self.assertEqual(_verify_google_credential("x" * 32, self.settings), claims)
        verify.assert_called_once()

    @patch("app.routers.auth.id_token.verify_oauth2_token")
    def test_unverified_google_email_is_rejected(self, verify):
        verify.return_value = {"iss": "https://accounts.google.com", "email_verified": False, "sub": "google-sub", "email": "person@example.com"}
        with self.assertRaises(HTTPException) as error:
            _verify_google_credential("x" * 32, self.settings)
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.detail["code"], "GOOGLE_EMAIL_UNVERIFIED")

    @patch("app.routers.auth.id_token.verify_oauth2_token")
    def test_wrong_issuer_is_rejected(self, verify):
        verify.return_value = {"iss": "https://evil.example", "email_verified": True, "sub": "google-sub", "email": "person@example.com"}
        with self.assertRaises(HTTPException) as error:
            _verify_google_credential("x" * 32, self.settings)
        self.assertEqual(error.exception.detail["code"], "GOOGLE_ISSUER_INVALID")


class AuthTokenTest(TestCase):
    def test_google_session_token_preserves_stage_roles(self):
        context = AuthContext(access_id=uuid4(), session_id=uuid4(), role="score_keeper", participant_id=uuid4(), available_roles=("score_keeper", "participant"))
        token = create_session_token(context, "test-secret", 60)
        restored = decode_session_token(token, "test-secret")
        self.assertEqual(restored.available_roles, ("score_keeper", "participant"))

    def test_legacy_token_is_rejected_by_api_authentication(self):
        context = AuthContext(access_id=uuid4(), session_id=uuid4(), role="coordinator")
        token = create_session_token(context, "test-secret", 60)
        with self.assertRaises(HTTPException) as error:
            asyncio.run(get_auth_context(f"Bearer {token}", Settings(session_secret="test-secret"), None))
        self.assertEqual(error.exception.detail["code"], "GOOGLE_LOGIN_REQUIRED")
