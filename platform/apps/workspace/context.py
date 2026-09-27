from apps.identity.api import current_user_id, user_label
from apps.teams.api import is_org_leader, organization_id_of, selected_team_id, visible_teams


def workspace(request):
    user_id = current_user_id(request)
    if user_id is None:
        return {}
    org_id = organization_id_of(user_id)
    selected = selected_team_id(user_id)
    teams = []
    selected_name = None
    for team in visible_teams(user_id):
        chosen = selected is not None and team.id == selected
        teams.append({"id": str(team.id), "name": team.name, "selected": chosen})
        if chosen:
            selected_name = team.name
    return {
        "nav_user_id": user_id,
        "nav_user_name": user_label(user_id),
        "nav_is_org_leader": bool(org_id and is_org_leader(user_id, org_id)),
        "nav_selected_team_id": None if selected is None else str(selected),
        "nav_selected_team_name": selected_name,
        "nav_teams": teams,
    }
