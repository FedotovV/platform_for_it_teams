import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.diagnostics.api import (
    FILL_BELOW_36,
    FILL_BELOW_51,
    FILL_BELOW_66,
    FILL_BELOW_85,
    FILL_FROM_85,
    share_paint,
)
from apps.diagnostics.models import ColorBound
from apps.teams.api import ROLE_MANAGER, ROLE_MEMBER
from apps.teams.models import Membership
from apps.teams.services import add_org_leader, add_person, create_organization, create_team


class SnapshotTests(TestCase):
    def setUp(self):
        self.org = create_organization("Организация")
        self.team = create_team(self.org, "Команда")
        self.manager = self._user("s5-manager", "Менеджер")
        self.member = self._user("s5-member", "Участник")
        self.org_leader = self._user("s5-org-leader", "Руководитель")
        Membership.objects.create(user_id=self.manager.id, team=self.team, role=ROLE_MANAGER)
        Membership.objects.create(user_id=self.member.id, team=self.team, role=ROLE_MEMBER)
        add_org_leader(self.org_leader.id, self.org)

    def _user(self, login, name):
        user = get_user_model().objects.create_user(login=login, name=name, password="password-1")
        add_person(user.id, self.org)
        return user

    def _login(self, login):
        self.client.logout()
        self.assertTrue(self.client.login(username=login, password="password-1"))

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def _survey(self, code, score):
        self._login("s5-manager")
        created = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        cycle_id = created.json()["id"]
        saved = self._post(
            f"/api/cycles/{cycle_id}/snapshot/",
            {"scale_version": None, "blocks": [{"code": code, "score": score}]},
        )
        self.assertEqual(saved.status_code, 200)
        self._post(f"/api/cycles/{cycle_id}/summary/", {"text": "План и следующие шаги"})
        self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self._post(f"/api/cycles/{cycle_id}/advance/", {})
        closed = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.json()["status"], "closed")
        return cycle_id

    def test_snapshots_stay_on_their_cycles_and_radar_has_no_color(self):
        first = self._survey("block-1", 2)
        second = self._survey("block-1", 5)
        self._login("s5-manager")
        older = self.client.get(f"/api/cycles/{first}/")
        self.assertEqual(older.json()["snapshot"]["blocks"], [{"code": "block-1", "score": 2, "color": None}])
        newer = self.client.get(f"/api/cycles/{second}/")
        self.assertEqual(newer.json()["snapshot"]["blocks"][0]["score"], 5)
        self.assertIsNone(newer.json()["snapshot"]["scale_version"])

        selected = self._post("/api/teams/selection/", {"team_id": str(self.team.id)})
        self.assertEqual(selected.status_code, 200)
        radar = self.client.get("/api/teams/selected/radar/")
        self.assertEqual(radar.status_code, 200)
        body = radar.json()
        self.assertEqual(body["snapshot"]["cycle_id"], second)
        self.assertIsNone(body["snapshot"]["blocks"][0]["color"])
        self.assertIsNone(body["snapshot"]["scale_maximum"])
        self.assertNotIn("votes", json.dumps(body))

        page = self.client.get("/teams/selected/radar/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "block-1: 5")

    def test_org_leader_gets_scores_without_votes(self):
        self._survey("block-1", 2)
        self._survey("block-1", 5)
        self._login("s5-org-leader")
        response = self.client.get(f"/api/organizations/{self.org.id}/snapshots/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        raw = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("votes", raw)
        self.assertNotIn("vote", raw)
        self.assertNotIn("голос", raw)
        team = body["teams"][0]
        self.assertEqual(team["latest"]["blocks"], [{"code": "block-1", "score": 5}])
        self.assertEqual(team["previous"]["blocks"], [{"code": "block-1", "score": 2}])
        self.assertNotIn("color", team["latest"]["blocks"][0])
        self._login("s5-member")
        denied = self.client.get(f"/api/organizations/{self.org.id}/snapshots/")
        self.assertEqual(denied.status_code, 403)

    def test_sector_color_follows_share_of_saved_maximum(self):
        self.assertEqual(share_paint(3.55, 10)["fill"], FILL_BELOW_36)
        self.assertEqual(share_paint(3.59, 10)["fill"], FILL_BELOW_36)
        self.assertEqual(share_paint(3.6, 10)["fill"], FILL_BELOW_51)
        self.assertEqual(share_paint(5.09, 10)["fill"], FILL_BELOW_51)
        self.assertEqual(share_paint(5.1, 10)["fill"], FILL_BELOW_66)
        self.assertEqual(share_paint(6.59, 10)["fill"], FILL_BELOW_66)
        self.assertEqual(share_paint(6.6, 10)["fill"], FILL_BELOW_85)
        self.assertEqual(share_paint(8.49, 10)["fill"], FILL_BELOW_85)
        self.assertEqual(share_paint(8.5, 10)["fill"], FILL_FROM_85)
        above = share_paint(12, 10)
        self.assertEqual(above["percent_text"], "100")
        self.assertEqual(above["fill"], FILL_FROM_85)
        self.assertEqual(above["ratio"], 1)
        self.assertIsNone(share_paint(None, 10))
        self.assertIsNone(share_paint("", 10))
        self.assertIsNone(share_paint(4, None))
        self.assertIsNone(share_paint(4, 0))

        self._login("s5-manager")
        created = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        cycle_id = created.json()["id"]
        saved = self._post(
            f"/api/cycles/{cycle_id}/snapshot/",
            {
                "scale_version": None,
                "scale_maximum": 10,
                "blocks": [{"code": "block-1", "score": 5}],
            },
        )
        self.assertEqual(saved.status_code, 200)
        body = saved.json()
        self.assertEqual(body["scale_maximum"], 10)
        self.assertEqual(body["blocks"], [{"code": "block-1", "score": 5, "color": None}])
        self.assertNotIn("chart_fill", body["blocks"][0])

    def test_color_bounds_are_not_seeded(self):
        self.assertFalse(ColorBound.objects.exists())
        root = Path(__file__).resolve().parents[1] / "diagnostics"
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in root.rglob("*")
            if path.suffix in {".py", ".html"} and path.name != "tests.py"
        ).lower()
        for word in ("красный", "жёлтый", "желтый", "зелёный", "зеленый", "red", "yellow", "green"):
            self.assertNotIn(word, text)
