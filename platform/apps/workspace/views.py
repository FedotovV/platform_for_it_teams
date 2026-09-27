from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.access.api import (
    CREATE_CYCLE,
    SET_SURVEY_INTERVAL,
    AccessError,
    can,
    grants_for,
    set_grant,
)
from apps.cycles.api import cycles_for_team
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
from apps.cycles.transitions import CycleError
from apps.cycles.views import cycle_payload
from apps.diagnostics.api import team_snapshot_pair
from apps.diagnostics.services import DiagnosticError, record_snapshot
from apps.history.api import changes_for
from apps.history.services import HistoryError, attachments_for, store_attachment, team_history
from apps.identity.api import current_user_id, user_id_by_login
from apps.problems.services import (
    ProblemError,
    actions_for_problem,
    add_action,
    carry_problem,
    load_action,
    load_problem,
    problems_for_team,
    raise_problem,
    set_action_status,
    set_problem_status,
)
from apps.teams.api import (
    is_org_leader,
    is_org_leader_of_team,
    membership_role,
    memberships_for,
    organization_id_of,
    select_team,
    visible_teams,
)
from apps.teams.services import TeamError, set_membership
from apps.workspace.common import actor_label, input_datetime, notice, parse_uuid, safe_next
from apps.workspace.labels import (
    ACTION_NAME,
    ACTION_STATUS,
    CYCLE_STATUS,
    KIND,
    LINK_KIND,
    NEXT_STATUS,
    PROBLEM_STATUS,
    ROLE,
    SOURCE,
    STATUS_BY_ENTITY,
)


def _changes(entity, object_id):
    labels = STATUS_BY_ENTITY[entity]
    rows = []
    for row in changes_for(entity, object_id):
        rows.append(
            {
                "from_label": labels.get(row["from_status"], row["from_status"]),
                "to_label": labels.get(row["to_status"], row["to_status"]),
                "from_status": row["from_status"],
                "to_status": row["to_status"],
                "actor_label": actor_label(row["actor_id"]),
                "at": row["at"],
            }
        )
    return rows


def _files(user_id, kind, object_id):
    rows = attachments_for(user_id, kind, object_id) or []
    return [{"id": row["id"], "filename": row["filename"]} for row in rows]


def select_team_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user_id = current_user_id(request)
    team_id = parse_uuid(request.POST.get("team_id"))
    if team_id is None or not select_team(user_id, team_id):
        return notice(request, "Команда не найдена", status=404)
    return redirect("workspace-team", team_id=team_id)


def team_page(request, team_id):
    user_id = current_user_id(request)
    team = visible_teams(user_id).filter(pk=team_id).first()
    if team is None:
        return notice(request, "Команда не найдена", status=404)
    error = None
    if request.method == "POST":
        error = _team_post(request, user_id, team)
        if error is None:
            return redirect("workspace-team", team_id=team.id)
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "workspace/team.html", _team_context(user_id, team, error))


def _team_post(request, user_id, team):
    form = request.POST.get("form")
    try:
        if form == "interval":
            raw = request.POST.get("interval_months", "")
            try:
                months = int(raw)
            except (TypeError, ValueError):
                return "Нужен интервал в месяцах"
            set_survey_interval(user_id, team.id, months)
            return None
        if form == "member":
            member_id = user_id_by_login(request.POST.get("login"))
            if member_id is None:
                return "Пользователь не найден"
            set_membership(user_id, team.id, member_id, request.POST.get("role"))
            return None
    except (CycleError, TeamError) as exc:
        return exc.detail
    return "Неизвестная форма"


def _team_context(user_id, team, error):
    role = membership_role(user_id, team.id)
    if role:
        role_label = ROLE[role]
    elif is_org_leader_of_team(user_id, team.id):
        role_label = "руководитель организации"
    else:
        role_label = ""
    members = []
    for row in memberships_for(user_id, team.id) or []:
        members.append(
            {
                "label": actor_label(row["user_id"]),
                "role_label": ROLE.get(row["role"], row["role"]),
            }
        )
    interval = survey_interval(user_id, team.id)
    return {
        "team": team,
        "error": error,
        "role_label": role_label,
        "members": members,
        "roles": ROLE.items(),
        "interval_months": interval.interval_months,
        "can_set_interval": can(user_id, team.id, SET_SURVEY_INTERVAL),
        "can_create_cycle": can(user_id, team.id, CREATE_CYCLE),
        "selected": str(team.id),
    }


def grants_page(request, team_id):
    user_id = current_user_id(request)
    team = visible_teams(user_id).filter(pk=team_id).first()
    if team is None:
        return notice(request, "Команда не найдена", status=404)
    error = None
    if request.method == "POST":
        try:
            set_grant(user_id, team.id, request.POST.get("action"), request.POST.get("role"))
        except AccessError as exc:
            error = exc.detail
        else:
            return redirect("workspace-grants", team_id=team.id)
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    grants = []
    for row in grants_for(team.id):
        grants.append(
            {
                "action_label": ACTION_NAME.get(row["action"], row["action"]),
                "role_label": ROLE.get(row["role"], row["role"]),
            }
        )
    return render(
        request,
        "workspace/grants.html",
        {
            "team": team,
            "error": error,
            "grants": grants,
            "actions": ACTION_NAME.items(),
            "roles": ROLE.items(),
        },
    )


def cycles_page(request):
    user_id = current_user_id(request)
    team = _selected(user_id)
    error = None
    if request.method == "POST":
        if team is None:
            error = "Сначала выберите команду."
        else:
            try:
                cycle = create_cycle(user_id, team.id, request.POST.get("kind"))
            except CycleError as exc:
                error = exc.detail
            else:
                return redirect("workspace-cycle", cycle_id=cycle.id)
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    cycles = []
    if team is not None:
        for row in team_history(user_id, team.id):
            row["kind_label"] = KIND.get(row["kind"], row["kind"])
            row["status_label"] = CYCLE_STATUS.get(row["status"], row["status"])
            cycles.append(row)
    return render(
        request,
        "workspace/cycles.html",
        {
            "team": team,
            "error": error,
            "cycles": cycles,
            "kinds": KIND.items(),
        },
    )


def cycle_page(request, cycle_id):
    user_id = current_user_id(request)
    cycle = load_visible(user_id, cycle_id)
    if cycle is None:
        return notice(request, "Цикл не найден", status=404)
    error = None
    if request.method == "POST":
        error = _cycle_post(request, user_id, cycle)
        if error is None:
            return redirect("workspace-cycle", cycle_id=cycle.id)
        cycle.refresh_from_db()
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "workspace/cycle.html", _cycle_context(user_id, cycle, error))


def _cycle_post(request, user_id, cycle):
    form = request.POST.get("form")
    try:
        if form == "schedule":
            parsed, failure = _posted_datetime(request.POST.get("scheduled_at"), allow_empty=True)
            if failure:
                return failure
            schedule(cycle, user_id, parsed)
            return None
        if form == "summary":
            require_advance(user_id, cycle)
            save_summary(cycle, request.POST.get("text") or "")
            return None
        if form == "advance":
            move_forward(cycle, user_id)
            return None
        if form == "review":
            require_advance(user_id, cycle)
            save_review_notes(cycle, {field: request.POST.get(field, "") for field in REVIEW_FIELDS})
            return None
        if form == "retro":
            require_advance(user_id, cycle)
            raw = request.POST.get("artifacts") or ""
            artifacts = [line.strip() for line in raw.splitlines() if line.strip()]
            save_retro(cycle, request.POST.get("plan") or "", artifacts)
            return None
        if form == "snapshot":
            blocks, failure = _posted_blocks(request.POST)
            if failure:
                return failure
            version = request.POST.get("scale_version")
            record_snapshot(user_id, cycle.id, version, blocks, request.POST.get("scale_maximum"))
            return None
    except (CycleError, DiagnosticError) as exc:
        return exc.detail
    return "Неизвестная форма"


def _posted_datetime(raw, allow_empty):
    if raw is None or str(raw).strip() == "":
        if allow_empty:
            return None, None
        return None, "Нужна дата и время"
    text = str(raw).strip()
    if len(text) == 16:
        text = text + ":00"
    parsed = parse_datetime(text)
    if parsed is None:
        return None, "Нужна дата и время"
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed, None


def _posted_blocks(post):
    blocks = []
    for index in range(6):
        code = (post.get(f"code_{index}") or "").strip()
        raw_score = (post.get(f"score_{index}") or "").strip()
        if not code and not raw_score:
            continue
        if not code or raw_score == "":
            return None, "Нужны код блока и балл"
        try:
            score = float(raw_score) if "." in raw_score else int(raw_score)
        except ValueError:
            return None, "Балл блока — число"
        blocks.append({"code": code, "score": score})
    if not blocks:
        return None, "Нужны баллы блоков"
    return blocks, None


def _cycle_context(user_id, cycle, error):
    payload = cycle_payload(cycle)
    payload["kind_label"] = KIND.get(payload["kind"], payload["kind"])
    payload["status_label"] = CYCLE_STATUS.get(payload["status"], payload["status"])
    payload["closed_by_label"] = actor_label(payload["closed_by"]) if payload["closed_by"] else ""
    payload["schedule_input"] = input_datetime(payload["scheduled_at"])
    review_values = payload.get("review") or {field: "" for field in REVIEW_FIELDS}
    retro = payload.get("retro") or {"plan": "", "artifacts": []}
    blocks = []
    scale_maximum = ""
    if payload.get("snapshot"):
        blocks = list(payload["snapshot"]["blocks"])
        if payload["snapshot"].get("scale_maximum") not in (None, ""):
            scale_maximum = payload["snapshot"]["scale_maximum"]
    while len(blocks) < 6:
        blocks.append({"code": "", "score": ""})
    return {
        "cycle": payload,
        "error": error,
        "next_label": NEXT_STATUS.get(payload["status"], ""),
        "review_fields": [
            ("plan_and_fact", "План и факт", review_values.get("plan_and_fact", "")),
            ("results", "Результаты", review_values.get("results", "")),
            ("deviation_causes", "Причины отклонений", review_values.get("deviation_causes", "")),
            ("changes", "Что изменяем", review_values.get("changes", "")),
            ("stops", "Что перестаём делать", review_values.get("stops", "")),
            ("reinforces", "Что усиливаем", review_values.get("reinforces", "")),
        ],
        "retro_plan": retro.get("plan", ""),
        "retro_artifacts": "\n".join(retro.get("artifacts") or []),
        "blocks": blocks[:6],
        "scale_maximum": scale_maximum,
        "changes": _changes("cycle", cycle.id),
        "files": _files(user_id, "cycle", cycle.id),
    }


def problems_page(request):
    user_id = current_user_id(request)
    team = _selected(user_id)
    error = None
    if request.method == "POST":
        if team is None:
            error = "Сначала выберите команду."
        else:
            cycle_raw = (request.POST.get("cycle_id") or "").strip()
            cycle_id = parse_uuid(cycle_raw) if cycle_raw else None
            if cycle_raw and cycle_id is None:
                error = "Цикл не найден"
            else:
                try:
                    problem = raise_problem(
                        user_id,
                        team.id,
                        request.POST.get("text"),
                        request.POST.get("source"),
                        request.POST.get("for_discussion") == "on",
                        request.POST.get("anonymous") == "on",
                        cycle_id,
                    )
                except ProblemError as exc:
                    error = exc.detail
                else:
                    return redirect("workspace-problem", problem_id=problem.id)
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    problems = []
    cycles = []
    if team is not None:
        for row in problems_for_team(user_id, team.id) or []:
            row["status_label"] = PROBLEM_STATUS.get(row["status"], row["status"])
            row["source_label"] = SOURCE.get(row["source"], row["source"])
            problems.append(row)
        cycles = _cycle_choices(team.id)
    return render(
        request,
        "workspace/problems.html",
        {
            "team": team,
            "error": error,
            "problems": problems,
            "cycles": cycles,
            "sources": SOURCE.items(),
        },
    )


def problem_page(request, problem_id):
    user_id = current_user_id(request)
    problem = load_problem(user_id, problem_id)
    if problem is None:
        return notice(request, "Проблема не найдена", status=404)
    error = None
    if request.method == "POST":
        error = _problem_post(request, user_id, problem)
        if error is None:
            return redirect("workspace-problem", problem_id=problem.id)
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "workspace/problem.html", _problem_context(user_id, problem, error))


def _problem_post(request, user_id, problem):
    form = request.POST.get("form")
    try:
        if form == "status":
            set_problem_status(user_id, problem.id, request.POST.get("status"))
            return None
        if form == "carry":
            cycle_id = parse_uuid(request.POST.get("cycle_id"))
            if cycle_id is None:
                return "Цикл не найден"
            carry_problem(user_id, problem.id, cycle_id)
            return None
        if form == "action":
            owner_id = parse_uuid(request.POST.get("owner_id"))
            if owner_id is None:
                return "Нужен владелец"
            due_at, failure = _posted_datetime(request.POST.get("due_at"), allow_empty=True)
            if failure:
                return failure
            add_action(user_id, problem.id, owner_id, due_at)
            return None
    except ProblemError as exc:
        return exc.detail
    return "Неизвестная форма"


def _problem_context(user_id, problem, error):
    from apps.problems.api import problem_payload

    payload = problem_payload(problem, user_id)
    payload["status_label"] = PROBLEM_STATUS.get(payload["status"], payload["status"])
    payload["source_label"] = SOURCE.get(payload["source"], payload["source"])
    if "author_id" in payload:
        payload["author_label"] = actor_label(payload["author_id"])
    links = []
    for link in payload["links"]:
        links.append(
            {
                "cycle_id": link["cycle_id"],
                "kind_label": LINK_KIND.get(link["kind"], link["kind"]),
            }
        )
    actions = []
    for row in actions_for_problem(user_id, problem.id) or []:
        row["status_label"] = ACTION_STATUS.get(row["status"], row["status"])
        row["owner_label"] = actor_label(row["owner_id"])
        row["due_input"] = input_datetime(row["due_at"])
        actions.append(row)
    members = []
    for row in memberships_for(user_id, problem.team_id) or []:
        members.append({"id": row["user_id"], "label": actor_label(row["user_id"])})
    return {
        "problem": payload,
        "error": error,
        "links": links,
        "actions": actions,
        "members": members,
        "cycles": _cycle_choices(problem.team_id),
        "statuses": PROBLEM_STATUS.items(),
        "changes": _changes("problem", problem.id),
        "files": _files(user_id, "problem", problem.id),
    }


def action_page(request, action_id):
    user_id = current_user_id(request)
    action = load_action(user_id, action_id)
    if action is None:
        return notice(request, "Действие не найдено", status=404)
    error = None
    if request.method == "POST":
        try:
            set_action_status(user_id, action.id, request.POST.get("status"))
        except ProblemError as exc:
            error = exc.detail
        else:
            return redirect("workspace-action", action_id=action.id)
    elif request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    from apps.problems.api import action_payload

    payload = action_payload(action)
    payload["status_label"] = ACTION_STATUS.get(payload["status"], payload["status"])
    payload["owner_label"] = actor_label(payload["owner_id"])
    payload["due_input"] = input_datetime(payload["due_at"])
    return render(
        request,
        "workspace/action.html",
        {
            "action": payload,
            "error": error,
            "statuses": ACTION_STATUS.items(),
            "changes": _changes("action", action.id),
            "files": _files(user_id, "action", action.id),
        },
    )


def organization_page(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    user_id = current_user_id(request)
    org_id = organization_id_of(user_id)
    if not is_org_leader(user_id, org_id):
        return notice(request, "Недостаточно прав", status=403)
    rows = []
    for team in visible_teams(user_id):
        latest, previous = team_snapshot_pair(team.id, with_color=False)
        rows.append(
            {
                "id": team.id,
                "name": team.name,
                "latest": latest,
                "previous": previous,
            }
        )
    return render(request, "workspace/organization.html", {"teams": rows})


def attachment_post(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user_id = current_user_id(request)
    nxt = safe_next(request.POST.get("next"))
    target_id = parse_uuid(request.POST.get("target_id"))
    upload = request.FILES.get("file")
    if upload is None or target_id is None:
        return render(
            request,
            "workspace/attachment_result.html",
            {"detail": "Нужны файл и объект", "next": nxt},
            status=400,
        )
    try:
        store_attachment(user_id, request.POST.get("target_kind"), target_id, upload)
    except HistoryError as exc:
        return render(
            request,
            "workspace/attachment_result.html",
            {"detail": exc.detail, "next": nxt},
            status=exc.status,
        )
    return redirect(nxt)


def _selected(user_id):
    from apps.teams.api import selected_team_id

    team_id = selected_team_id(user_id)
    if team_id is None:
        return None
    return visible_teams(user_id).filter(pk=team_id).first()


def _cycle_choices(team_id):
    choices = []
    for row in cycles_for_team(team_id):
        choices.append(
            {
                "id": row["id"],
                "label": f"{KIND.get(row['kind'], row['kind'])}, {CYCLE_STATUS.get(row['status'], row['status'])}",
            }
        )
    return choices
