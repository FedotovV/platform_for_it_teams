import uuid

from django.http import FileResponse, HttpResponseNotAllowed

from apps.history.api import ENTITIES, changes_for
from apps.history.services import HistoryError, open_attachment, store_attachment, team_history
from apps.identity.api import current_user_id
from apps.teams.api import can_see_team
from config.responses import respond


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def history_api(request, team_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    try:
        cycles = team_history(current_user_id(request), team_id)
    except HistoryError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond({"cycles": cycles})


def history_page(request, team_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    from django.shortcuts import render

    user_id = current_user_id(request)
    cycles = []
    if can_see_team(user_id, team_id):
        cycles = team_history(user_id, team_id)
    return render(request, "history/history.html", {"cycles": cycles, "team_id": team_id})


def attachments_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    upload = request.FILES.get("file")
    target_id = _uuid(request.POST.get("target_id"))
    if upload is None or target_id is None:
        return respond({"detail": "Нужны файл и объект"}, status=400)
    try:
        row = store_attachment(
            current_user_id(request),
            request.POST.get("target_kind"),
            target_id,
            upload,
        )
    except HistoryError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(
        {
            "id": str(row.id),
            "target_kind": row.target_kind,
            "target_id": str(row.target_id),
            "filename": row.filename,
        },
        status=201,
    )


def attachment_view(request, attachment_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    try:
        row, path = open_attachment(current_user_id(request), attachment_id)
    except HistoryError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    handle = path.open("rb")
    return FileResponse(handle, as_attachment=True, filename=row.filename)


def status_changes_view(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    entity = request.GET.get("entity")
    object_id = _uuid(request.GET.get("object_id"))
    if entity not in ENTITIES or object_id is None:
        return respond({"detail": "Нужны сущность и объект"}, status=400)
    from apps.history.services import object_team_id

    team_id = object_team_id(entity, object_id)
    if team_id is None or not can_see_team(current_user_id(request), team_id):
        return respond({"detail": "Объект не найден"}, status=404)
    return respond({"changes": changes_for(entity, object_id)})
