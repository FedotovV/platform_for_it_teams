import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.problems.models import Problem
from apps.teams.api import ROLE_MANAGER, ROLE_MEMBER
from apps.teams.models import Membership
from apps.teams.services import add_person, create_organization, create_team


class ProblemTests(TestCase):
    def setUp(self):
        self.org = create_organization("Организация")
        self.team = create_team(self.org, "Команда")
        self.manager = self._user("s6-manager", "Менеджер")
        self.member = self._user("s6-member", "Участник")
        Membership.objects.create(user_id=self.manager.id, team=self.team, role=ROLE_MANAGER)
        Membership.objects.create(user_id=self.member.id, team=self.team, role=ROLE_MEMBER)

    def _user(self, login, name):
        user = get_user_model().objects.create_user(login=login, name=name, password="password-1")
        add_person(user.id, self.org)
        return user

    def _login(self, login):
        self.client.logout()
        self.assertTrue(self.client.login(username=login, password="password-1"))

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def _cycle(self):
        self._login("s6-manager")
        created = self._post("/api/cycles/", {"team_id": str(self.team.id), "kind": "survey"})
        self.assertEqual(created.status_code, 201)
        return created.json()["id"]

    def test_anonymous_author_is_hidden_and_carry_is_a_link(self):
        origin = self._cycle()
        nxt = self._cycle()
        self._login("s6-manager")
        created = self._post(
            "/api/problems/",
            {
                "team_id": str(self.team.id),
                "text": "Слабое место",
                "source": "manual",
                "for_discussion": True,
                "anonymous": True,
                "cycle_id": origin,
            },
        )
        self.assertEqual(created.status_code, 201)
        body = created.json()
        problem_id = body["id"]
        self.assertEqual(body["author_id"], str(self.manager.id))
        self.assertEqual(body["status"], "raised")
        stored = Problem.objects.get(pk=problem_id)
        self.assertEqual(stored.author_id, self.manager.id)

        self._login("s6-member")
        seen = self.client.get(f"/api/problems/{problem_id}/")
        self.assertEqual(seen.status_code, 200)
        self.assertNotIn("author_id", seen.json())
        self.assertEqual(seen.json()["anonymous"], True)
        refused = self._post(f"/api/problems/{problem_id}/carry/", {"cycle_id": nxt})
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.json(), {"detail": "Недостаточно прав"})
        self.assertFalse(stored.links.filter(kind="carried").exists())

        self._login("s6-manager")
        carried = self._post(f"/api/problems/{problem_id}/carry/", {"cycle_id": nxt})
        self.assertEqual(carried.status_code, 200)
        payload = carried.json()
        self.assertEqual(payload["status"], "raised")
        kinds = {link["kind"] for link in payload["links"]}
        self.assertEqual(kinds, {"raised", "carried"})
        self.assertNotIn("carried", {code for code, _label in Problem.STATUSES})

    def test_due_date_and_closed_cycle_do_not_move_the_action(self):
        cycle_id = self._cycle()
        self._login("s6-manager")
        problem = self._post(
            "/api/problems/",
            {
                "team_id": str(self.team.id),
                "text": "Слабое место",
                "source": "survey",
                "anonymous": False,
                "cycle_id": cycle_id,
            },
        )
        problem_id = problem.json()["id"]
        blocked = self._post(f"/api/problems/{problem_id}/status/", {"status": "in_progress"})
        self.assertEqual(blocked.status_code, 400)
        action = self._post(
            f"/api/problems/{problem_id}/actions/",
            {"owner_id": str(self.member.id), "due_at": "2020-01-01T00:00:00Z"},
        )
        self.assertEqual(action.status_code, 201)
        self.assertEqual(action.json()["status"], "assigned")
        action_id = action.json()["id"]
        again = self.client.get(f"/api/actions/{action_id}/")
        self.assertEqual(again.json()["status"], "assigned")
        self.assertTrue(again.json()["due_at"].startswith("2020-01-01"))

        self._post(f"/api/cycles/{cycle_id}/summary/", {"text": "План и следующие шаги"})
        self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self._post(f"/api/cycles/{cycle_id}/advance/", {})
        closed = self._post(f"/api/cycles/{cycle_id}/advance/", {})
        self.assertEqual(closed.json()["status"], "closed")
        after = self.client.get(f"/api/actions/{action_id}/")
        self.assertEqual(after.status_code, 200)
        self.assertEqual(after.json()["status"], "assigned")
