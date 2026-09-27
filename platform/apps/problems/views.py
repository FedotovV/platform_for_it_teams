import uuid

from django.http import HttpResponseNotAllowed
from django.utils.dateparse import parse_datetime

from apps.identity.api import current_user_id
from apps.problems.api import action_payload, problem_payload
from apps.problems.services import (
    ProblemError,
    add_action,
    carry_problem,
    load_action,
    load_problem,
    raise_problem,
    set_action_status,
    set_problem_status,
)
from config.responses import loads_object, respond


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def problems_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    team_id = _uuid(body.get("team_id"))
    if team_id is None:
        return respond({"detail": "Нужна команда"}, status=400)
    cycle_id = body.get("cycle_id")
    if cycle_id is not None:
        cycle_id = _uuid(cycle_id)
        if cycle_id is None:
            return respond({"detail": "Цикл не найден"}, status=404)
    try:
        problem = raise_problem(
            current_user_id(request),
            team_id,
            body.get("text"),
            body.get("source"),
            body.get("for_discussion", False),
            body.get("anonymous", False),
            cycle_id,
        )
    except ProblemError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(problem_payload(problem, current_user_id(request)), status=201)


def problem_view(request, problem_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    problem = load_problem(current_user_id(request), problem_id)
    if problem is None:
        return respond({"detail": "Проблема не найдена"}, status=404)
    return respond(problem_payload(problem, current_user_id(request)))


def problem_status_view(request, problem_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = loads_object(request)
    if body is None or "status" not in body:
        return respond({"detail": "Нужен статус"}, status=400)
    try:
        problem = set_problem_status(current_user_id(request), problem_id, body.get("status"))
    except ProblemError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(problem_payload(problem, current_user_id(request)))


def carry_view(request, problem_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    cycle_id = _uuid(body.get("cycle_id"))
    if cycle_id is None:
        return respond({"detail": "Цикл не найден"}, status=404)
    try:
        problem = carry_problem(current_user_id(request), problem_id, cycle_id)
    except ProblemError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(problem_payload(problem, current_user_id(request)))


def actions_view(request, problem_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = loads_object(request)
    if body is None:
        return respond({"detail": "Нужно тело JSON"}, status=400)
    owner_id = _uuid(body.get("owner_id"))
    if owner_id is None:
        return respond({"detail": "Нужен владелец"}, status=400)
    due_at = None
    if body.get("due_at") is not None:
        due_at = parse_datetime(str(body.get("due_at")))
        if due_at is None:
            return respond({"detail": "Нужна дата срока"}, status=400)
    try:
        action = add_action(current_user_id(request), problem_id, owner_id, due_at)
    except ProblemError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(action_payload(action), status=201)


def action_view(request, action_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    action = load_action(current_user_id(request), action_id)
    if action is None:
        return respond({"detail": "Действие не найдено"}, status=404)
    return respond(action_payload(action))


def action_status_view(request, action_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    body = loads_object(request)
    if body is None or "status" not in body:
        return respond({"detail": "Нужен статус"}, status=400)
    try:
        action = set_action_status(current_user_id(request), action_id, body.get("status"))
    except ProblemError as exc:
        return respond({"detail": exc.detail}, status=exc.status)
    return respond(action_payload(action))
