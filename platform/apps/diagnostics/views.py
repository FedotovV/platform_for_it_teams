import uuid

from django.http import HttpResponseNotAllowed
from django.shortcuts import render

from apps.diagnostics.api import BAND_LEGEND, present_blocks, snapshot_for, team_snapshot_pair
from apps.diagnostics.services import DiagnosticError, record_snapshot
from apps.identity.api import current_user_id
from apps.teams.api import (
    can_see_team,
    is_org_leader,
    organization_team_ids,
    selected_team_id,
)
from config.responses import loads_object, respond


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def snapshot_view(request, cycle_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    try:
        record_snapshot(
            current_user_id(request),
            cycle_id,
            body.get("scale_version"),
            body.get("blocks"),
            body.get("scale_maximum"),
        )
    except DiagnosticError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(snapshot_for(cycle_id))


def radar_api(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    user_id = current_user_id(request)
    team_id = selected_team_id(user_id)
    if team_id is None or not can_see_team(user_id, team_id):
        return respond({"detail": "Команда не выбрана"}, status=404)
    latest, _previous = team_snapshot_pair(team_id, with_color=True)
    return respond({"team_id": str(team_id), "snapshot": latest})


def radar_page(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    user_id = current_user_id(request)
    team_id = selected_team_id(user_id)
    snapshot = None
    if team_id is not None and can_see_team(user_id, team_id):
        snapshot, _previous = team_snapshot_pair(team_id, with_color=True)
        if snapshot is not None:
            snapshot = present_blocks(snapshot)
    return render(
        request,
        "diagnostics/radar.html",
        {"team_id": team_id, "snapshot": snapshot, "band_legend": BAND_LEGEND},
    )


def org_snapshots(request, organization_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    user_id = current_user_id(request)
    if not is_org_leader(user_id, organization_id):
        return respond({"detail": "Недостаточно прав"}, status=403)
    teams = []
    for team_id in organization_team_ids(organization_id):
        latest, previous = team_snapshot_pair(team_id, with_color=False)
        teams.append(
            {
                "team_id": str(team_id),
                "latest": latest,
                "previous": previous,
            }
        )
    return respond({"organization_id": str(organization_id), "teams": teams})
