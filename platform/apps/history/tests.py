import json
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.history.models import Attachment
from apps.teams.api import ROLE_MANAGER, ROLE_MEMBER
from apps.teams.models import Membership
from apps.teams.services import add_person, create_organization, create_team


class HistoryTests(TestCase):
    def setUp(self):
        self.org = create_organization("Организация")
        self.other = create_organization("Другая")
        self.team = create_team(self.org, "Команда")
        self.foreign = create_team(self.other, "Чужая")
        self.manager = self._user("s7-manager", "Менеджер", self.org)
        self.member = self._user("s7-member", "Участник", self.org)
        self.outsider = self._user("s7-outsider", "Чужой", self.other)
        Membership.objects.create(user_id=self.manager.id, team=self.team, role=ROLE_MANAGER)
        Membership.objects.create(user_id=self.member.id, team=self.team, role=ROLE_MEMBER)
        Membership.objects.create(user_id=self.outsider.id, team=self.foreign, role=ROLE_MEMBER)
        self.files = tempfile.TemporaryDirectory()
        self.settings = override_settings(ATTACHMENT_ROOT=self.files.name)
        self.settings.enable()

    def tearDown(self):
        self.settings.disable()
        self.files.cleanup()

    def _user(self, login, name, organization):
        user = get_user_model().objects.create_user(login=login, name=name, password="password-1")
        add_person(user.id, organization)
        return user

    def _login(self, login):
        self.client.logout()
        self.assertTrue(self.client.login(username=login, password="password-1"))

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def _closed_survey(self, score):
        self._login("s7-manager")
        created = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        cycle_id = created.json()["id"]
        self._post(
            f"/api/cycles/{cycle_id}/snapshot/",
            {"scale_version": None, "blocks": [{"code": "block-1", "score": score}]},
        )
        self._post(f"/api/cycles/{cycle_id}/summary/", {"text": "План и следующие шаги"})
        self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self._post(f"/api/cycles/{cycle_id}/advance/", {})
        closed = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(closed.json()["status"], "closed")
        return cycle_id

    def test_history_shows_both_closed_surveys_and_their_snapshots(self):
        first = self._closed_survey(2)
        second = self._closed_survey(5)
        self._login("s7-manager")
        opened = self.client.get(f"/api/cycles/{first}/")
        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.json()["status"], "closed")
        history = self.client.get(f"/api/teams/{self.team.id}/history/")
        self.assertEqual(history.status_code, 200)
        rows = {row["id"]: row for row in history.json()["cycles"]}
        self.assertEqual(rows[first]["snapshot"]["blocks"][0]["score"], 2)
        self.assertEqual(rows[second]["snapshot"]["blocks"][0]["score"], 5)
        self.assertEqual(rows[first]["status"], "closed")
        self.assertEqual(rows[second]["status"], "closed")
        page = self.client.get(f"/teams/{self.team.id}/history/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "block-1: 2")
        self.assertContains(page, "block-1: 5")
        changes = self.client.get(f"/api/status-changes/?entity=cycle&object_id={first}")
        self.assertEqual(changes.status_code, 200)
        pairs = [(row["from_status"], row["to_status"]) for row in changes.json()["changes"]]
        self.assertEqual(pairs, [("draft", "collect"), ("collect", "review"), ("review", "closed")])

    def test_attachment_stays_inside_the_team_and_known_objects(self):
        self._login("s7-manager")
        problem = self._post(
            "/api/problems/",
            {
                "team_id": str(self.team.id),
                "text": "Слабое место",
                "source": "manual",
                "anonymous": False,
            },
        )
        problem_id = problem.json()["id"]
        uploaded = self.client.post(
            "/api/attachments/",
            {
                "target_kind": "problem",
                "target_id": problem_id,
                "file": SimpleUploadedFile("note.txt", b"fixture"),
            },
        )
        self.assertEqual(uploaded.status_code, 201)
        attachment_id = uploaded.json()["id"]
        own = self.client.get(f"/api/attachments/{attachment_id}/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(b"".join(own.streaming_content), b"fixture")

        self._login("s7-outsider")
        hidden = self.client.get(f"/api/attachments/{attachment_id}/")
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json(), {"detail": "Вложение не найдено"})

        self._login("s7-manager")
        refused = self.client.post(
            "/api/attachments/",
            {
                "target_kind": "team",
                "target_id": str(self.team.id),
                "file": SimpleUploadedFile("note.txt", b"fixture"),
            },
        )
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(
            refused.json(),
            {"detail": "Вложение можно добавить только к проблеме, действию или циклу"},
        )
        self.assertFalse(Attachment.objects.filter(target_kind="team").exists())
