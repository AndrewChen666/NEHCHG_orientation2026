from unittest import TestCase

from app.main import app


class RouteContractTest(TestCase):
    def test_google_orientation_routes_exist_without_code_login(self):
        paths = set(app.openapi()["paths"])
        expected = {
            "/api/v1/auth/google",
            "/api/v1/auth/me",
            "/api/v1/setup/sessions/{session_id}/participants/import",
            "/api/v1/setup/sessions/{session_id}/stages",
            "/api/v1/setup/sessions/{session_id}/role-assignments",
            "/api/v1/stages/{stage_id}/icebreaker/groups",
            "/api/v1/stages/{stage_id}/scores",
            "/api/v1/sessions/{session_id}/leaderboards",
        }
        self.assertTrue(expected.issubset(paths))
        self.assertNotIn("/api/v1/auth/code-login", paths)
