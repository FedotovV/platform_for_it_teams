from apps.teams.models import Membership, OrgLeadership, Person, SelectedTeam, Team

ROLE_MANAGER = Membership.ROLE_MANAGER
ROLE_LEADER = Membership.ROLE_LEADER
ROLE_MEMBER = Membership.ROLE_MEMBER
ROLE_FACILITATOR = Membership.ROLE_FACILITATOR
TEAM_ROLES = {
    ROLE_MANAGER,
    ROLE_LEADER,
    ROLE_MEMBER,
    ROLE_FACILITATOR,
}


def organization_id_of(user_id):
    person = Person.objects.filter(user_id=user_id).first()
    if person is None:
        return None
    return person.organization_id


def membership_role(user_id, team_id):
    row = Membership.objects.filter(user_id=user_id, team_id=team_id).first()
    if row is None:
        return None
    return row.role


def team_organization_id(team_id):
    team = Team.objects.filter(pk=team_id).first()
    if team is None:
        return None
    return team.organization_id


def is_org_leader(user_id, organization_id):
    if organization_id is None:
        return False
    return OrgLeadership.objects.filter(
        user_id=user_id,
        organization_id=organization_id,
    ).exists()


def is_org_leader_of_team(user_id, team_id):
    return is_org_leader(user_id, team_organization_id(team_id))


def visible_teams(user_id):
    """Команды, которые этот пользователь может видеть. Без полей голосов."""
    org_id = organization_id_of(user_id)
    if org_id is None:
        return Team.objects.none()

    team_ids = set(
        Membership.objects.filter(
            user_id=user_id,
            team__organization_id=org_id,
        ).values_list("team_id", flat=True)
    )
    if is_org_leader(user_id, org_id):
        team_ids.update(
            Team.objects.filter(organization_id=org_id).values_list("id", flat=True)
        )
    return Team.objects.filter(id__in=team_ids, organization_id=org_id).order_by("name", "id")


def can_see_team(user_id, team_id):
    return visible_teams(user_id).filter(pk=team_id).exists()


def team_payload(team):
    return {
        "id": str(team.id),
        "name": team.name,
        "organization_id": str(team.organization_id),
    }


def selected_team_id(user_id):
    row = SelectedTeam.objects.filter(user_id=user_id).first()
    if row is None:
        return None
    if not can_see_team(user_id, row.team_id):
        row.delete()
        return None
    return row.team_id


def select_team(user_id, team_id):
    if not can_see_team(user_id, team_id):
        return False
    SelectedTeam.objects.update_or_create(
        user_id=user_id,
        defaults={"team_id": team_id},
    )
    return True
