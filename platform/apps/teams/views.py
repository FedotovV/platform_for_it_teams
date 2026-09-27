import uuid

from django.http import HttpResponseNotAllowed

from apps.identity.api import current_user_id
from apps.teams import api
from apps.teams.services import TeamError, set_membership
from config.responses import loads_object, respond


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def teams_view(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    user_id = current_user_id(request)
    teams = [api.team_payload(team) for team in api.visible_teams(user_id)]
    selected = api.selected_team_id(user_id)
    return respond(
        {
            "selected_team_id": None if selected is None else str(selected),
            "teams": teams,
        }
    )


def team_view(request, team_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    user_id = current_user_id(request)
    if not api.can_see_team(user_id, team_id):
        return respond({"detail": "Команда не найдена"}, status=404)
    team = api.visible_teams(user_id).get(pk=team_id)
    return respond(api.team_payload(team))


def selection_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user_id = current_user_id(request)
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    team_id = _uuid(body.get("team_id"))
    if team_id is None:
        return respond({"detail": "Нужна команда"}, status=400)
    if not api.select_team(user_id, team_id):
        return respond({"detail": "Команда не найдена"}, status=404)
    return respond({"selected_team_id": str(team_id)})


def memberships_view(request, team_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user_id = current_user_id(request)
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    member_id = _uuid(body.get("user_id"))
    if member_id is None:
        return respond({"detail": "Нужен пользователь"}, status=400)
    try:
        membership = set_membership(user_id, team_id, member_id, body.get("role"))
    except TeamError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(
        {
            "user_id": str(membership.user_id),
            "team_id": str(membership.team_id),
            "role": membership.role,
        }
    )
