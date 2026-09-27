from apps.access.api import ADVANCE_CYCLE, CREATE_CYCLE, SET_SURVEY_INTERVAL, can
from apps.cycles.models import Cycle, CycleSummary, RetroRecord, ReviewNotes, TeamSurveySettings

REVIEW_FIELDS = (
    "plan_and_fact",
    "results",
    "deviation_causes",
    "changes",
    "stops",
    "reinforces",
)
from apps.cycles.transitions import CycleError, advance, set_schedule
from apps.teams.api import can_see_team


def create_cycle(user_id, team_id, kind):
    if kind not in {Cycle.KIND_SURVEY, Cycle.KIND_REVIEW, Cycle.KIND_RETRO}:
        raise CycleError("Неизвестный вид цикла")
    if not can_see_team(user_id, team_id):
        raise CycleError("Команда не найдена", status=404)
    if not can(user_id, team_id, CREATE_CYCLE):
        raise CycleError("Недостаточно прав", status=403)
    return Cycle.objects.create(
        team_id=team_id,
        kind=kind,
        status=Cycle.STATUS_DRAFT,
    )


def load_visible(user_id, cycle_id):
    cycle = Cycle.objects.filter(pk=cycle_id).first()
    if cycle is None or not can_see_team(user_id, cycle.team_id):
        return None
    return cycle


def require_advance(user_id, cycle):
    if not can(user_id, cycle.team_id, ADVANCE_CYCLE):
        raise CycleError("Недостаточно прав", status=403)


def save_summary(cycle, text):
    if cycle.kind not in (Cycle.KIND_SURVEY, Cycle.KIND_REVIEW):
        raise CycleError("Резюме пишется на опросе и ревью")
    if text is None:
        raise CycleError("Нужно резюме")
    summary, _created = CycleSummary.objects.update_or_create(
        cycle=cycle,
        defaults={"text": text},
    )
    return summary


def save_review_notes(cycle, data):
    if cycle.kind != Cycle.KIND_REVIEW:
        raise CycleError("Состав ревью пишется только на ревью")
    values = {}
    for field in REVIEW_FIELDS:
        raw = data.get(field, "")
        if not isinstance(raw, str):
            raise CycleError("Блок ревью — текст")
        values[field] = raw
    notes, _created = ReviewNotes.objects.update_or_create(cycle=cycle, defaults=values)
    return notes


def save_retro(cycle, plan, artifacts):
    if cycle.kind != Cycle.KIND_RETRO:
        raise CycleError("План ретро пишется только на ретро")
    if not isinstance(plan, str):
        raise CycleError("Нужен план ретро")
    if artifacts is None:
        artifacts = []
    if not isinstance(artifacts, list) or any(not isinstance(item, str) for item in artifacts):
        raise CycleError("Артефакты — список текстов")
    record, _created = RetroRecord.objects.update_or_create(
        cycle=cycle,
        defaults={"plan": plan, "artifacts": artifacts},
    )
    return record


def survey_interval(user_id, team_id):
    if not can_see_team(user_id, team_id):
        raise CycleError("Команда не найдена", status=404)
    row, _created = TeamSurveySettings.objects.get_or_create(
        team_id=team_id,
        defaults={"interval_months": TeamSurveySettings.QUARTER_MONTHS},
    )
    return row


def set_survey_interval(user_id, team_id, months):
    if not can_see_team(user_id, team_id):
        raise CycleError("Команда не найдена", status=404)
    if not can(user_id, team_id, SET_SURVEY_INTERVAL):
        raise CycleError("Недостаточно прав", status=403)
    if isinstance(months, bool) or not isinstance(months, int) or months < 1:
        raise CycleError("Интервал — целое число месяцев от 1")
    row, _created = TeamSurveySettings.objects.get_or_create(
        team_id=team_id,
        defaults={"interval_months": TeamSurveySettings.QUARTER_MONTHS},
    )
    row.interval_months = months
    row.save(update_fields=["interval_months"])
    return row


def move_forward(cycle, user_id):
    require_advance(user_id, cycle)
    return advance(cycle, user_id)


def schedule(cycle, user_id, scheduled_at):
    require_advance(user_id, cycle)
    return set_schedule(cycle, scheduled_at)
