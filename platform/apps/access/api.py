from apps.access.models import TeamGrant
from apps.teams import api as teams_api

CREATE_CYCLE = "create_cycle"
KNOWN_ACTIONS = {CREATE_CYCLE}
CREATE_CYCLE_DENIED_ROLES = {teams_api.ROLE_MEMBER, teams_api.ROLE_FACILITATOR}
DEFAULT_CREATE_CYCLE_ROLES = (teams_api.ROLE_MANAGER, teams_api.ROLE_LEADER)


class AccessError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status


def seed_default_grants(team_id):
    for role in DEFAULT_CREATE_CYCLE_ROLES:
        TeamGrant.objects.get_or_create(
            team_id=team_id,
            action=CREATE_CYCLE,
            role=role,
        )


def can_manage_roster(user_id, team_id):
    if not teams_api.can_see_team(user_id, team_id):
        return False
    if teams_api.is_org_leader_of_team(user_id, team_id):
        return True
    return teams_api.membership_role(user_id, team_id) == teams_api.ROLE_MANAGER


def can(user_id, team_id, action):
    """Проверка действия команды. Создание цикла участником и фасилитатором закрыто в коде."""
    if action not in KNOWN_ACTIONS:
        return False
    if not teams_api.can_see_team(user_id, team_id):
        return False
    role = teams_api.membership_role(user_id, team_id)
    if action == CREATE_CYCLE and role in CREATE_CYCLE_DENIED_ROLES:
        return False
    if role is None:
        return False
    return TeamGrant.objects.filter(team_id=team_id, action=action, role=role).exists()


def grants_for(team_id):
    rows = TeamGrant.objects.filter(team_id=team_id).order_by("action", "role")
    return [{"action": row.action, "role": row.role} for row in rows]


def set_grant(actor_id, team_id, action, role):
    if action not in KNOWN_ACTIONS:
        raise AccessError("Неизвестное действие", status=404)
    if role not in teams_api.TEAM_ROLES:
        raise AccessError("Неизвестная роль")
    if not teams_api.can_see_team(actor_id, team_id):
        raise AccessError("Команда не найдена", status=404)
    if not can_manage_roster(actor_id, team_id):
        raise AccessError("Недостаточно прав", status=403)
    if action == CREATE_CYCLE and role in CREATE_CYCLE_DENIED_ROLES:
        raise AccessError("Эту роль нельзя назначить на создание цикла")
    _grant, _created = TeamGrant.objects.get_or_create(
        team_id=team_id,
        action=action,
        role=role,
    )
    return {"action": action, "role": role}
