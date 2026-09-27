import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.access.api import CREATE_CYCLE, can
from apps.access.models import TeamGrant
from apps.teams.api import (
    ROLE_FACILITATOR,
    ROLE_LEADER,
    ROLE_MANAGER,
    ROLE_MEMBER,
)
from apps.teams.models import Membership
from apps.teams.services import (
    add_org_leader,
    add_person,
    create_organization,
    create_team,
)


class TeamAccessTests(TestCase):
    def setUp(self):
        self.org = create_organization("Организация")
        self.other = create_organization("Другая")
        self.team_a = create_team(self.org, "Команда 1")
        self.team_b = create_team(self.org, "Команда 2")
        self.team_c = create_team(self.org, "Команда 3")
        self.foreign = create_team(self.other, "Чужая")

        self.manager = self._user("s2-manager", "Менеджер", self.org)
        self.leader = self._user("s2-leader", "Лидер", self.org)
        self.member = self._user("s2-member", "Участник", self.org)
        self.facilitator = self._user("s2-facilitator", "Фасилитатор", self.org)
        self.org_leader = self._user("s2-org-leader", "Руководитель", self.org)
        self.outsider = self._user("s2-outsider", "Чужой", self.other)
        self.recruit = self._user("s2-recruit", "Новый", self.org)

        self._join(self.manager, self.team_a, ROLE_MANAGER)
        self._join(self.manager, self.team_b, ROLE_MANAGER)
        self._join(self.leader, self.team_c, ROLE_LEADER)
        self._join(self.member, self.team_c, ROLE_MEMBER)
        self._join(self.facilitator, self.team_c, ROLE_FACILITATOR)
        self._join(self.outsider, self.foreign, ROLE_MEMBER)
        add_org_leader(self.org_leader.id, self.org)

    def _join(self, user, team, role):
        Membership.objects.create(user_id=user.id, team=team, role=role)

    def _user(self, login, name, organization):
        user = get_user_model().objects.create_user(login=login, name=name, password="password-1")
        add_person(user.id, organization)
        return user

    def _login(self, login):
        self.client.logout()
        self.assertTrue(self.client.login(username=login, password="password-1"))

    def _team_ids(self, response):
        self.assertEqual(response.status_code, 200)
        return {row["id"] for row in response.json()["teams"]}

    def test_manager_switches_only_own_teams(self):
        self._login("s2-manager")
        listed = self.client.get("/api/teams/")
        self.assertEqual(
            self._team_ids(listed),
            {str(self.team_a.id), str(self.team_b.id)},
        )
        self.assertIsNone(listed.json()["selected_team_id"])
        self.assertEqual(set(listed.json().keys()), {"selected_team_id", "teams"})

        switched = self.client.post(
            "/api/teams/selection/",
            data=json.dumps({"team_id": str(self.team_b.id)}),
            content_type="application/json",
        )
        self.assertEqual(switched.status_code, 200)
        self.assertEqual(switched.json(), {"selected_team_id": str(self.team_b.id)})
        again = self.client.get("/api/teams/")
        self.assertEqual(again.json()["selected_team_id"], str(self.team_b.id))

        denied = self.client.post(
            "/api/teams/selection/",
            data=json.dumps({"team_id": str(self.team_c.id)}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(self.client.get("/api/teams/").json()["selected_team_id"], str(self.team_b.id))

    def test_leader_and_member_see_their_teams(self):
        self._login("s2-leader")
        self.assertEqual(self._team_ids(self.client.get("/api/teams/")), {str(self.team_c.id)})
        self._login("s2-member")
        self.assertEqual(self._team_ids(self.client.get("/api/teams/")), {str(self.team_c.id)})

    def test_org_leader_sees_org_teams_without_votes(self):
        self._login("s2-org-leader")
        response = self.client.get("/api/teams/")
        self.assertEqual(
            self._team_ids(response),
            {str(self.team_a.id), str(self.team_b.id), str(self.team_c.id)},
        )
        body = response.json()
        self.assertNotIn("votes", body)
        self.assertNotIn("голоса", json.dumps(body, ensure_ascii=False))
        for team in body["teams"]:
            self.assertEqual(set(team.keys()), {"id", "name", "organization_id"})

    def test_other_organization_does_not_receive_teams(self):
        self._login("s2-outsider")
        self.assertEqual(self._team_ids(self.client.get("/api/teams/")), {str(self.foreign.id)})
        hidden = self.client.get(f"/api/teams/{self.team_a.id}/")
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(hidden.json(), {"detail": "Команда не найдена"})

    def test_member_cannot_create_cycle_even_with_a_grant_row(self):
        TeamGrant.objects.create(
            team_id=self.team_c.id,
            action=CREATE_CYCLE,
            role=ROLE_MEMBER,
        )
        self.assertFalse(can(self.member.id, self.team_c.id, CREATE_CYCLE))
        self._login("s2-member")
        response = self.client.get(f"/api/teams/{self.team_c.id}/actions/create_cycle/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"action": "create_cycle", "allowed": False})

    def test_matrix_does_not_grant_create_cycle_to_member_or_facilitator(self):
        self._login("s2-manager")
        for role in (ROLE_MEMBER, ROLE_FACILITATOR):
            response = self.client.post(
                f"/api/teams/{self.team_a.id}/grants/",
                data=json.dumps({"action": "create_cycle", "role": role}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(
            TeamGrant.objects.filter(
                team_id=self.team_a.id,
                action=CREATE_CYCLE,
                role__in=[ROLE_MEMBER, ROLE_FACILITATOR],
            ).exists()
        )

    def test_facilitator_cannot_change_roster_or_grants(self):
        self._login("s2-facilitator")
        roster = self.client.post(
            f"/api/teams/{self.team_c.id}/memberships/",
            data=json.dumps({"user_id": str(self.recruit.id), "role": ROLE_MEMBER}),
            content_type="application/json",
        )
        self.assertEqual(roster.status_code, 403)
        self.assertEqual(roster.json(), {"detail": "Недостаточно прав"})
        grants = self.client.post(
            f"/api/teams/{self.team_c.id}/grants/",
            data=json.dumps({"action": "create_cycle", "role": ROLE_LEADER}),
            content_type="application/json",
        )
        self.assertEqual(grants.status_code, 403)
        self.assertFalse(
            TeamGrant.objects.filter(team_id=self.team_c.id, role=ROLE_FACILITATOR).exists()
        )

    def test_manager_can_create_cycle_by_default_grant(self):
        self._login("s2-manager")
        response = self.client.get(f"/api/teams/{self.team_a.id}/actions/create_cycle/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"action": "create_cycle", "allowed": True})
