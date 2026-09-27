import ast
from pathlib import Path

from django.apps import apps
from django.test import TestCase

from apps.identity.api import current_user_id
from apps.identity.models import User

EMPTY_APPS = ("history",)


class HealthTests(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class SessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            login="manager",
            name="Менеджер",
            password="password-1",
        )

    def test_login_and_logout(self):
        anonymous = self.client.get("/")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/login/", anonymous.url)
        self.assertIsNone(current_user_id(anonymous.wsgi_request))

        logged_in = self.client.post(
            "/login/",
            {"login": "manager", "password": "password-1"},
        )
        self.assertRedirects(logged_in, "/")
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, str(self.user.id))
        self.assertEqual(current_user_id(home.wsgi_request), self.user.id)

        logged_out = self.client.post("/logout/")
        self.assertRedirects(logged_out, "/login/")
        after = self.client.get("/")
        self.assertEqual(after.status_code, 302)
        self.assertIsNone(current_user_id(after.wsgi_request))

    def test_wrong_password_does_not_open_session(self):
        response = self.client.post(
            "/login/",
            {"login": "manager", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный логин или пароль.")
        home = self.client.get("/")
        self.assertEqual(home.status_code, 302)


class EmptyModuleTests(TestCase):
    def setUp(self):
        User.objects.create_user(login="manager", name="Менеджер", password="password-1")

    def test_later_modules_have_no_models(self):
        for label in EMPTY_APPS:
            self.assertEqual(list(apps.get_app_config(label).get_models()), [])

    def test_teams_path_is_absent(self):
        self.assertEqual(self.client.get("/teams/").status_code, 404)
        self.client.post("/login/", {"login": "manager", "password": "password-1"})
        self.assertEqual(self.client.get("/teams/").status_code, 404)

    def test_other_apps_do_not_import_identity_models(self):
        apps_dir = Path(__file__).resolve().parents[1]
        for path in apps_dir.rglob("*.py"):
            if "identity" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn("identity.models", node.module)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn("identity.models", alias.name)
