from django.http import HttpResponseNotAllowed

from apps.access.api import (
    KNOWN_ACTIONS,
    AccessError,
    can,
    can_manage_roster,
    grants_for,
    set_grant,
)
from apps.identity.api import current_user_id
from apps.teams.api import can_see_team
from config.responses import loads_object, respond


def grants_view(request, team_id):
    user_id = current_user_id(request)
    if not can_see_team(user_id, team_id):
        return respond({"detail": "Команда не найдена"}, status=404)
    if request.method == "GET":
        return respond({"grants": grants_for(team_id)})
    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])
    if not can_manage_roster(user_id, team_id):
        return respond({"detail": "Недостаточно прав"}, status=403)
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    try:
        grant = set_grant(user_id, team_id, body.get("action"), body.get("role"))
    except AccessError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(grant)


def action_view(request, team_id, action_code):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    user_id = current_user_id(request)
    if action_code not in KNOWN_ACTIONS:
        return respond({"detail": "Неизвестное действие"}, status=404)
    if not can_see_team(user_id, team_id):
        return respond({"detail": "Команда не найдена"}, status=404)
    allowed = can(user_id, team_id, action_code)
    status = 200 if allowed else 403
    return respond({"action": action_code, "allowed": allowed}, status=status)
