import re

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.cycles.models import Cycle
from apps.teams.api import ROLE_LEADER, ROLE_MANAGER, ROLE_MEMBER
from apps.teams.models import Membership
from apps.teams.services import add_org_leader, add_person, create_organization, create_team


class UiSmoke(TestCase):
    def test_paths(self):
        org = create_organization("Фикстура-организация")
        other = create_organization("Фикстура-чужая")
        alpha = create_team(org, "Фикстура-альфа")
        beta = create_team(org, "Фикстура-бета")
        foreign = create_team(other, "Фикстура-чужая-команда")
        User = get_user_model()

        def user(login, name, organization):
            account = User.objects.create_user(login=login, name=name, password="fixture-pass-1")
            add_person(account.id, organization)
            return account

        manager = user("fix-manager", "Менеджер фикстуры", org)
        member = user("fix-member", "Участник фикстуры", org)
        user("fix-leader", "Лидер фикстуры", org)
        user("fix-org", "Руководитель фикстуры", org)
        user("fix-out", "Чужой фикстуры", other)
        Membership.objects.create(user_id=manager.id, team=alpha, role=ROLE_MANAGER)
        Membership.objects.create(user_id=manager.id, team=beta, role=ROLE_MANAGER)
        Membership.objects.create(user_id=member.id, team=alpha, role=ROLE_MEMBER)
        leader = User.objects.get(login="fix-leader")
        Membership.objects.create(user_id=leader.id, team=alpha, role=ROLE_LEADER)
        add_org_leader(User.objects.get(login="fix-org").id, org)
        Membership.objects.create(
            user_id=User.objects.get(login="fix-out").id,
            team=foreign,
            role=ROLE_MEMBER,
        )

        def login(name):
            self.client.logout()
            self.assertTrue(self.client.login(username=name, password="fixture-pass-1"))

        login("fix-manager")
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        text = home.content.decode()
        self.assertIn("Фикстура-альфа", text)
        self.assertNotIn("Фикстура-чужая-команда", text)
        selected = self.client.post("/workspace/teams/select/", {"team_id": str(alpha.id)})
        self.assertEqual(selected.status_code, 302)
        team = self.client.get(f"/workspace/teams/{alpha.id}/")
        self.assertContains(team, "не добавляется")
        self.assertContains(team, "3")
        self.assertEqual(self.client.get(f"/workspace/teams/{alpha.id}/grants/").status_code, 200)

        created = self.client.post("/workspace/cycles/", {"kind": "survey"})
        self.assertEqual(created.status_code, 302)
        cycle_url = created.url
        page = self.client.get(cycle_url)
        self.assertContains(page, "черновик")
        self.client.post(cycle_url, {"form": "schedule", "scheduled_at": "2026-09-27T10:00"})
        page = self.client.get(cycle_url)
        self.assertContains(page, "черновик")
        self.assertContains(page, "2026-09-27")
        self.client.post(cycle_url, {"form": "advance"})
        self.client.post(cycle_url, {"form": "advance"})
        failed = self.client.post(cycle_url, {"form": "advance"})
        self.assertEqual(failed.status_code, 200)
        self.assertContains(failed, "Нужно резюме")
        self.assertContains(failed, "разбор")
        self.client.post(cycle_url, {"form": "summary", "text": "План и следующие шаги"})
        snap = self.client.post(
            cycle_url,
            {
                "form": "snapshot",
                "scale_version": "",
                "scale_maximum": "10",
                "code_0": "block-1",
                "score_0": "2",
            },
        )
        self.assertEqual(snap.status_code, 302, snap.content[:400])
        closed = self.client.post(cycle_url, {"form": "advance"})
        self.assertEqual(closed.status_code, 302, closed.content[:400])
        page = self.client.get(cycle_url)
        self.assertContains(page, "закрыт")
        self.assertContains(page, "Менеджер фикстуры")
        self.assertContains(page, "черновик → сбор")

        second = self.client.post("/workspace/cycles/", {"kind": "survey"})
        url2 = second.url
        cycle2_id = url2.rstrip("/").rsplit("/", 1)[-1]
        self.client.post(
            url2,
            {"form": "snapshot", "code_0": "block-1", "score_0": "5", "scale_maximum": "10"},
        )
        problem = self.client.post(
            "/workspace/problems/",
            {
                "text": "Слабое место",
                "source": "survey",
                "cycle_id": cycle2_id,
                "anonymous": "on",
            },
        )
        self.assertEqual(problem.status_code, 302, problem.content[:500])
        purl = problem.url
        page = self.client.get(purl)
        self.assertContains(page, "Менеджер фикстуры")
        action = self.client.post(
            purl,
            {"form": "action", "owner_id": str(member.id), "due_at": "2020-01-01T00:00"},
        )
        self.assertEqual(action.status_code, 302, action.content[:500])
        page = self.client.get(purl)
        self.assertContains(page, "назначено")
        self.assertContains(page, "2020-01-01")
        self.client.post(url2, {"form": "summary", "text": "План и следующие шаги"})
        self.client.post(url2, {"form": "advance"})
        self.client.post(url2, {"form": "advance"})
        self.client.post(url2, {"form": "advance"})
        page = self.client.get(purl)
        self.assertContains(page, "назначено")
        action_href = re.search(r'href="(/workspace/actions/[^"]+)"', page.content.decode()).group(1)
        action_page = self.client.get(action_href)
        self.assertContains(action_page, "назначено")
        self.assertContains(action_page, "2020-01-01")

        history = self.client.get(f"/teams/{alpha.id}/history/")
        self.assertContains(history, "block-1: 2")
        self.assertContains(history, "block-1: 5")
        self.assertContains(history, "закрыт")
        first = self.client.get(cycle_url)
        self.assertContains(first, "закрыт")

        radar = self.client.get("/teams/selected/radar/")
        self.assertContains(radar, "block-1: 5")
        self.assertContains(radar, 'id="scale-maximum">10<')
        self.assertContains(radar, "#e07a2f")
        self.assertNotContains(radar, "Цвет секторов не задан")
        self.assertNotContains(radar, "красный")

        review = self.client.post("/workspace/cycles/", {"kind": "review"})
        rurl = review.url
        self.client.post(
            rurl,
            {
                "form": "review",
                "plan_and_fact": "план и факт",
                "results": "результаты",
                "deviation_causes": "причины",
                "changes": "изменяем",
                "stops": "перестаём",
                "reinforces": "усиливаем",
            },
        )
        self.client.post(rurl, {"form": "summary", "text": "Резюме итогов"})
        self.client.post(rurl, {"form": "schedule", "scheduled_at": "2026-10-01T12:00"})
        self.client.post(rurl, {"form": "advance"})
        self.client.post(rurl, {"form": "advance"})
        done = self.client.post(rurl, {"form": "advance"})
        self.assertEqual(done.status_code, 302, done.content[:400])
        page = self.client.get(rurl)
        self.assertContains(page, "закрыт")
        self.assertContains(page, "план и факт")
        self.assertContains(page, "Резюме итогов")

        retro = self.client.post("/workspace/cycles/", {"kind": "retro"})
        turl = retro.url
        self.client.post(turl, {"form": "schedule", "scheduled_at": "2026-10-02T15:00"})
        self.client.post(turl, {"form": "advance"})
        self.client.post(turl, {"form": "advance"})
        blocked = self.client.post(turl, {"form": "advance"})
        self.assertContains(blocked, "Нужен план ретро")
        self.client.post(turl, {"form": "retro", "plan": "План ретро", "artifacts": "доска\nфото"})
        self.client.post(turl, {"form": "advance"})
        page = self.client.get(turl)
        self.assertContains(page, "закрыт")
        self.assertContains(page, "План ретро")
        self.assertContains(page, "доска")
        self.assertContains(page, "2026-10-02")

        login("fix-member")
        home = self.client.get("/")
        text = home.content.decode()
        self.assertIn("Фикстура-альфа", text)
        self.assertNotIn("Фикстура-бета", text)
        self.client.post("/workspace/teams/select/", {"team_id": str(alpha.id)})
        denied = self.client.post("/workspace/cycles/", {"kind": "survey"})
        self.assertContains(denied, "Недостаточно прав")
        page = self.client.get(purl)
        self.assertContains(page, "Автор скрыт")
        author_line = page.content.decode().split('id="author-line"', 1)[1].split("</p>", 1)[0]
        self.assertNotIn("Менеджер фикстуры", author_line)
        self.assertNotIn(str(manager.id), author_line)
        target = Cycle.objects.filter(team_id=alpha.id).first()
        carried = self.client.post(purl, {"form": "carry", "cycle_id": str(target.id)})
        self.assertContains(carried, "Недостаточно прав")
        self.assertNotContains(self.client.get(purl), "перенесена в цикл")
        org_page = self.client.get("/workspace/organization/")
        self.assertEqual(org_page.status_code, 403)

        login("fix-org")
        home = self.client.get("/")
        text = home.content.decode()
        self.assertIn("Фикстура-альфа", text)
        self.assertIn("Фикстура-бета", text)
        self.assertNotIn("Фикстура-чужая-команда", text)
        aggregates = self.client.get("/workspace/organization/")
        self.assertEqual(aggregates.status_code, 200)
        self.assertContains(aggregates, "block-1: 5")
        self.assertContains(aggregates, "block-1: 2")
        self.assertNotContains(aggregates, "голос")
        raw = aggregates.content.decode().lower()
        self.assertNotIn("vote", raw)

        login("fix-leader")
        home = self.client.get("/")
        text = home.content.decode()
        self.assertIn("Фикстура-альфа", text)
        self.assertNotIn("Фикстура-бета", text)

        login("fix-out")
        home = self.client.get("/")
        text = home.content.decode()
        self.assertIn("Фикстура-чужая-команда", text)
        self.assertNotIn("Фикстура-альфа", text)

        login("fix-manager")
        problem_id = purl.rstrip("/").rsplit("/", 1)[-1]
        uploaded = self.client.post(
            "/workspace/attachments/",
            {
                "target_kind": "problem",
                "target_id": problem_id,
                "next": purl,
                "file": SimpleUploadedFile("note.txt", b"fixture-body"),
            },
        )
        self.assertEqual(uploaded.status_code, 302, uploaded.content[:400])
        page = self.client.get(purl)
        self.assertContains(page, "note.txt")
        link = re.search(r'href="(/api/attachments/[^"]+)"', page.content.decode()).group(1)
        own = self.client.get(link)
        self.assertEqual(own.status_code, 200)
        login("fix-out")
        hidden = self.client.get(link)
        self.assertEqual(hidden.status_code, 404)
        self.assertContains(hidden, "Вложение не найдено", status_code=404)
        login("fix-manager")
        refused = self.client.post(
            "/workspace/attachments/",
            {
                "target_kind": "team",
                "target_id": str(alpha.id),
                "next": "/",
                "file": SimpleUploadedFile("note.txt", b"fixture-body"),
            },
        )
        self.assertEqual(refused.status_code, 400)
        self.assertContains(
            refused,
            "Вложение можно добавить только к проблеме, действию или циклу",
            status_code=400,
        )
        print("SMOKE OK")


