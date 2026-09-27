import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.teams.api import ROLE_FACILITATOR, ROLE_MANAGER, ROLE_MEMBER
from apps.teams.models import Membership
from apps.teams.services import add_person, create_organization, create_team


class SurveyCycleTests(TestCase):
    def setUp(self):
        self.org = create_organization("Организация")
        self.other = create_organization("Другая")
        self.team = create_team(self.org, "Команда")
        self.foreign = create_team(self.other, "Чужая")
        self.manager = self._user("s3-manager", "Менеджер", self.org)
        self.member = self._user("s3-member", "Участник", self.org)
        self.facilitator = self._user("s3-facilitator", "Фасилитатор", self.org)
        self.outsider = self._user("s3-outsider", "Чужой", self.other)
        self._join(self.manager, self.team, ROLE_MANAGER)
        self._join(self.member, self.team, ROLE_MEMBER)
        self._join(self.facilitator, self.team, ROLE_FACILITATOR)
        self._join(self.outsider, self.foreign, ROLE_MEMBER)

    def _user(self, login, name, organization):
        user = get_user_model().objects.create_user(login=login, name=name, password="password-1")
        add_person(user.id, organization)
        return user

    def _join(self, user, team, role):
        Membership.objects.create(user_id=user.id, team=team, role=role)

    def _login(self, login):
        self.client.logout()
        self.assertTrue(self.client.login(username=login, password="password-1"))

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def test_survey_path_on_one_team(self):
        self._login("s3-manager")
        self.assertEqual(self.client.get(f"/api/teams/{self.team.id}/").status_code, 200)
        self._login("s3-member")
        self.assertEqual(self.client.get(f"/api/teams/{self.team.id}/").status_code, 200)
        self._login("s3-outsider")
        self.assertEqual(self.client.get(f"/api/teams/{self.team.id}/").status_code, 404)

        self._login("s3-member")
        refused = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.json(), {"detail": "Недостаточно прав"})

        self._login("s3-manager")
        created = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["kind"], "survey")
        self.assertEqual(body["status"], "draft")
        self.assertIsNone(body["scheduled_at"])
        self.assertIsNone(body["closed_by"])
        cycle_id = body["id"]

        dated = self._post(
            f"/api/cycles/{cycle_id}/schedule/",
            {"scheduled_at": "2020-01-01T00:00:00Z"},
        )
        self.assertEqual(dated.status_code, 200)
        self.assertEqual(dated.json()["status"], "draft")
        self.assertTrue(dated.json()["scheduled_at"].startswith("2020-01-01"))

        collected = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(collected.status_code, 200)
        self.assertEqual(collected.json()["status"], "collect")
        reviewed = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.json()["status"], "review")

        refused_close = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(refused_close.status_code, 400)
        self.assertEqual(refused_close.json()["detail"], "Нужно резюме: план и следующие шаги")
        self.assertEqual(self.client.get(f"/api/cycles/{cycle_id}/").json()["status"], "review")

        summary = self._post(
            f"/api/cycles/{cycle_id}/summary/",
            {"text": "План и следующие шаги"},
        )
        self.assertEqual(summary.status_code, 200)
        closed = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(closed.status_code, 200)
        closed_body = closed.json()
        self.assertEqual(closed_body["status"], "closed")
        self.assertEqual(closed_body["closed_by"], str(self.manager.id))
        self.assertIsNotNone(closed_body["closed_at"])
        self.assertEqual(closed_body["summary"], "План и следующие шаги")

        second = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(second.json()["id"], cycle_id)
        self.assertEqual(second.json()["status"], "draft")
        first = self.client.get(f"/api/cycles/{cycle_id}/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "closed")

        shifted = self._post(
            f"/api/cycles/{cycle_id}/schedule/",
            {"scheduled_at": "2019-05-01T00:00:00Z"},
        )
        self.assertEqual(shifted.status_code, 200)
        self.assertEqual(shifted.json()["status"], "closed")
        self.assertEqual(shifted.json()["closed_by"], str(self.manager.id))

    def test_new_team_interval_is_quarter_and_override_is_stored(self):
        self._login("s3-manager")
        current = self.client.get(f"/api/teams/{self.team.id}/survey-interval/")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json(), {"team_id": str(self.team.id), "interval_months": 3})
        updated = self.client.put(
            f"/api/teams/{self.team.id}/survey-interval/",
            data=json.dumps({"interval_months": 6}),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["interval_months"], 6)
        again = self.client.get(f"/api/teams/{self.team.id}/survey-interval/")
        self.assertEqual(again.json()["interval_months"], 6)

    def test_review_kind_is_not_created_yet(self):
        self._login("s3-manager")
        response = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "review"})
        self.assertEqual(response.status_code, 400)

    def test_facilitator_advances_existing_cycle_and_does_not_create(self):
        self._login("s3-manager")
        created = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        cycle_id = created.json()["id"]
        self._login("s3-facilitator")
        refused = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        self.assertEqual(refused.status_code, 403)
        moved = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["status"], "collect")
