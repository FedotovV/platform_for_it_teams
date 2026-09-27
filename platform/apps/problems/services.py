from apps.access.api import CARRY_PROBLEM, can
from apps.cycles.api import cycle_brief
from apps.identity.api import user_exists
from apps.problems.models import Action, Problem, ProblemCycleLink
from apps.teams.api import can_see_team

SOURCES = {code for code, _label in Problem.SOURCES}
PROBLEM_STATUSES = {code for code, _label in Problem.STATUSES}
ACTION_STATUSES = {code for code, _label in Action.STATUSES}


class ProblemError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status


def _visible_problem(user_id, problem_id):
    problem = Problem.objects.filter(pk=problem_id).first()
    if problem is None or not can_see_team(user_id, problem.team_id):
        return None
    return problem


def _cycle_on_team(cycle_id, team_id):
    brief = cycle_brief(cycle_id)
    if brief is None or brief["team_id"] != team_id:
        raise ProblemError("Цикл не найден", status=404)
    return brief


def raise_problem(user_id, team_id, text, source, for_discussion, anonymous, cycle_id):
    if not can_see_team(user_id, team_id):
        raise ProblemError("Команда не найдена", status=404)
    text = (text or "").strip() if isinstance(text, str) else ""
    if not text:
        raise ProblemError("Нужен текст проблемы")
    if source not in SOURCES:
        raise ProblemError("Неизвестный источник")
    if not isinstance(for_discussion, bool) or not isinstance(anonymous, bool):
        raise ProblemError("Нужны логические поля")
    if cycle_id is not None:
        _cycle_on_team(cycle_id, team_id)
    problem = Problem.objects.create(
        team_id=team_id,
        text=text,
        source=source,
        for_discussion=for_discussion,
        anonymous=anonymous,
        author_id=user_id,
        status=Problem.STATUS_RAISED,
    )
    if cycle_id is not None:
        ProblemCycleLink.objects.create(
            problem=problem,
            cycle_id=cycle_id,
            kind=ProblemCycleLink.KIND_RAISED,
        )
    return problem


def load_problem(user_id, problem_id):
    return _visible_problem(user_id, problem_id)


def set_problem_status(user_id, problem_id, status):
    problem = _visible_problem(user_id, problem_id)
    if problem is None:
        raise ProblemError("Проблема не найдена", status=404)
    if status not in PROBLEM_STATUSES:
        raise ProblemError("Неизвестный статус")
    if status == Problem.STATUS_IN_PROGRESS and not problem.actions.exists():
        raise ProblemError("Нужно действие, чтобы поставить проблему в работу")
    previous = problem.status
    if previous == status:
        return problem
    problem.status = status
    problem.save(update_fields=["status"])
    from apps.history.api import record_status_change

    record_status_change("problem", problem.id, previous, status, user_id)
    return problem


def carry_problem(user_id, problem_id, cycle_id):
    problem = _visible_problem(user_id, problem_id)
    if problem is None:
        raise ProblemError("Проблема не найдена", status=404)
    if not can(user_id, problem.team_id, CARRY_PROBLEM):
        raise ProblemError("Недостаточно прав", status=403)
    _cycle_on_team(cycle_id, problem.team_id)
    ProblemCycleLink.objects.get_or_create(
        problem=problem,
        cycle_id=cycle_id,
        kind=ProblemCycleLink.KIND_CARRIED,
    )
    problem.refresh_from_db()
    return problem


def add_action(user_id, problem_id, owner_id, due_at):
    problem = _visible_problem(user_id, problem_id)
    if problem is None:
        raise ProblemError("Проблема не найдена", status=404)
    if not user_exists(owner_id):
        raise ProblemError("Пользователь не найден", status=404)
    action = Action.objects.create(
        problem=problem,
        owner_id=owner_id,
        due_at=due_at,
        status=Action.STATUS_ASSIGNED,
    )
    return action


def load_action(user_id, action_id):
    action = Action.objects.filter(pk=action_id).select_related("problem").first()
    if action is None or not can_see_team(user_id, action.problem.team_id):
        return None
    return action


def set_action_status(user_id, action_id, status):
    action = load_action(user_id, action_id)
    if action is None:
        raise ProblemError("Действие не найдено", status=404)
    if status not in ACTION_STATUSES:
        raise ProblemError("Неизвестный статус")
    previous = action.status
    if previous == status:
        return action
    action.status = status
    action.save(update_fields=["status"])
    from apps.history.api import record_status_change

    record_status_change("action", action.id, previous, status, user_id)
    return action
