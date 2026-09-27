import uuid

from django.http import HttpResponseNotAllowed
from django.utils.dateparse import parse_datetime

from apps.cycles.models import Cycle, CycleSummary, RetroRecord, ReviewNotes
from apps.cycles.services import (
    REVIEW_FIELDS,
    create_cycle,
    load_visible,
    move_forward,
    require_advance,
    save_retro,
    save_review_notes,
    save_summary,
    schedule,
    set_survey_interval,
    survey_interval,
)
from apps.cycles.transitions import CycleError, outcome_missing_detail
from apps.identity.api import current_user_id
from config.responses import loads_object, respond


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _dt(value):
    if value is None:
        return None
    return value.isoformat()


def cycle_payload(cycle):
    try:
        summary = cycle.summary.text
    except CycleSummary.DoesNotExist:
        summary = None
    payload = {
        "id": str(cycle.id),
        "team_id": str(cycle.team_id),
        "kind": cycle.kind,
        "status": cycle.status,
        "scheduled_at": _dt(cycle.scheduled_at),
        "closed_at": _dt(cycle.closed_at),
        "closed_by": None if cycle.closed_by is None else str(cycle.closed_by),
        "summary": summary,
    }
    if cycle.kind == Cycle.KIND_REVIEW:
        payload["review"] = _review_payload(cycle)
    if cycle.kind == Cycle.KIND_RETRO:
        payload["retro"] = _retro_payload(cycle)
    if cycle.kind == Cycle.KIND_SURVEY:
        from apps.diagnostics.api import snapshot_for

        payload["snapshot"] = snapshot_for(cycle.id)
    return payload


def _review_payload(cycle):
    try:
        notes = cycle.review_notes
    except ReviewNotes.DoesNotExist:
        return {field: "" for field in REVIEW_FIELDS}
    return {field: getattr(notes, field) for field in REVIEW_FIELDS}


def _retro_payload(cycle):
    try:
        record = cycle.retro_record
    except RetroRecord.DoesNotExist:
        return {"plan": "", "artifacts": []}
    return {"plan": record.plan, "artifacts": record.artifacts}


def cycles_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    team_id = _uuid(body.get("team_id"))
    if team_id is None:
        return respond({"detail": "Нужна команда"}, status=400)
    try:
        cycle = create_cycle(current_user_id(request), team_id, body.get("kind"))
    except CycleError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(cycle_payload(cycle), status=201)


def cycle_view(request, cycle_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    cycle = load_visible(current_user_id(request), cycle_id)
    if cycle is None:
        return respond({"detail": "Цикл не найден"}, status=404)
    return respond(cycle_payload(cycle))


def schedule_view(request, cycle_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cycle = load_visible(current_user_id(request), cycle_id)
    if cycle is None:
        return respond({"detail": "Цикл не найден"}, status=404)
    body = loads_object(request)
    if body is None or "scheduled_at" not in body:
        return respond({"detail": "Нужна дата и время"}, status=400)
    raw = body.get("scheduled_at")
    if raw is None:
        parsed = None
    else:
        parsed = parse_datetime(str(raw))
        if parsed is None:
            return respond({"detail": "Нужна дата и время"}, status=400)
    try:
        schedule(cycle, current_user_id(request), parsed)
    except CycleError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    cycle.refresh_from_db()
    return respond(cycle_payload(cycle))


def summary_view(request, cycle_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cycle = load_visible(current_user_id(request), cycle_id)
    if cycle is None:
        return respond({"detail": "Цикл не найден"}, status=404)
    body = loads_object(request)
    if body is None or "text" not in body or not isinstance(body.get("text"), str):
        return respond({"detail": outcome_missing_detail(cycle.kind)}, status=400)
    try:
        require_advance(current_user_id(request), cycle)
        save_summary(cycle, body.get("text"))
    except CycleError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    cycle.refresh_from_db()
    return respond(cycle_payload(cycle))


def advance_view(request, cycle_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cycle = load_visible(current_user_id(request), cycle_id)
    if cycle is None:
        return respond({"detail": "Цикл не найден"}, status=404)
    try:
        move_forward(cycle, current_user_id(request))
    except CycleError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    cycle.refresh_from_db()
    return respond(cycle_payload(cycle))


def review_view(request, cycle_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cycle = load_visible(current_user_id(request), cycle_id)
    if cycle is None:
        return respond({"detail": "Цикл не найден"}, status=404)
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    try:
        require_advance(current_user_id(request), cycle)
        save_review_notes(cycle, body)
    except CycleError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    cycle.refresh_from_db()
    return respond(cycle_payload(cycle))


def retro_view(request, cycle_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    cycle = load_visible(current_user_id(request), cycle_id)
    if cycle is None:
        return respond({"detail": "Цикл не найден"}, status=404)
    body = loads_object(request)
    if body is None or "plan" not in body:
        return respond({"detail": "Нужен план ретро"}, status=400)
    try:
        require_advance(current_user_id(request), cycle)
        save_retro(cycle, body.get("plan"), body.get("artifacts"))
    except CycleError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    cycle.refresh_from_db()
    return respond(cycle_payload(cycle))


def interval_view(request, team_id):
    user_id = current_user_id(request)
    try:
        if request.method == "GET":
            row = survey_interval(user_id, team_id)
        elif request.method == "PUT":
            body = loads_object(request)
            if body is None or "interval_months" not in body:
                return respond({"detail": "Нужен интервал в месяцах"}, status=400)
            row = set_survey_interval(user_id, team_id, body.get("interval_months"))
        else:
            return HttpResponseNotAllowed(["GET", "PUT"])
    except CycleError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond({"team_id": str(row.team_id), "interval_months": row.interval_months})
