from apps.identity.api import user_exists
from apps.teams.api import TEAM_ROLES, organization_id_of
from apps.teams.models import Membership, Organization, OrgLeadership, Person, Team


class TeamError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status


def create_organization(name):
    name = (name or "").strip()
    if not name:
        raise TeamError("Нужно название организации")
    return Organization.objects.create(name=name)


def add_person(user_id, organization):
    if not user_exists(user_id):
        raise TeamError("Пользователь не найден", status=404)
    existing = Person.objects.filter(user_id=user_id).first()
    if existing is not None:
        if existing.organization_id != organization.id:
            raise TeamError("Человек уже в другой организации")
        return existing
    return Person.objects.create(user_id=user_id, organization=organization)


def add_org_leader(user_id, organization):
    person = Person.objects.filter(user_id=user_id).first()
    if person is None or person.organization_id != organization.id:
        raise TeamError("Руководитель должен быть человеком этой организации")
    row, _created = OrgLeadership.objects.get_or_create(
        user_id=user_id,
        organization=organization,
    )
    return row


def create_team(organization, name):
    name = (name or "").strip()
    if not name:
        raise TeamError("Нужно название команды")
    team = Team.objects.create(organization=organization, name=name)
    from apps.access.api import seed_default_grants

    seed_default_grants(team.id)
    return team


def set_membership(actor_id, team_id, user_id, role):
    from apps.access.api import can_manage_roster
    from apps.teams.api import can_see_team

    team = Team.objects.filter(pk=team_id).first()
    if team is None or not can_see_team(actor_id, team_id):
        raise TeamError("Команда не найдена", status=404)
    if not can_manage_roster(actor_id, team_id):
        raise TeamError("Недостаточно прав", status=403)
    if role not in TEAM_ROLES:
        raise TeamError("Неизвестная роль")
    if not user_exists(user_id):
        raise TeamError("Пользователь не найден", status=404)
    if organization_id_of(user_id) != team.organization_id:
        raise TeamError("Нужен человек этой организации")
    membership, _created = Membership.objects.update_or_create(
        user_id=user_id,
        team=team,
        defaults={"role": role},
    )
    return membership
