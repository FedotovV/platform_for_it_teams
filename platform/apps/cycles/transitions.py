from django.utils import timezone

from apps.cycles.models import Cycle, CycleSummary, RetroRecord

# Единственное место переходов статуса. Обработчики экрана сюда не пишут правила.
FORWARD = (
    Cycle.STATUS_DRAFT,
    Cycle.STATUS_COLLECT,
    Cycle.STATUS_REVIEW,
    Cycle.STATUS_CLOSED,
)


class CycleError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status


def advance(cycle, user_id):
    if cycle.status not in FORWARD:
        raise CycleError("Неизвестный статус цикла")
    index = FORWARD.index(cycle.status)
    if index >= len(FORWARD) - 1:
        raise CycleError("Цикл уже закрыт")
    target = FORWARD[index + 1]
    if target == Cycle.STATUS_CLOSED and not _outcome_recorded(cycle):
        raise CycleError(outcome_missing_detail(cycle.kind))
    previous = cycle.status
    cycle.status = target
    if target == Cycle.STATUS_CLOSED:
        cycle.closed_at = timezone.now()
        cycle.closed_by = user_id
    cycle.save()
    from apps.history.api import record_status_change

    record_status_change("cycle", cycle.id, previous, target, user_id)
    return cycle


def set_schedule(cycle, scheduled_at):
    """Дата хранится рядом со статусом и сама статус не меняет."""
    cycle.scheduled_at = scheduled_at
    cycle.save(update_fields=["scheduled_at"])
    return cycle


def outcome_missing_detail(kind):
    if kind == Cycle.KIND_RETRO:
        return "Нужен план ретро"
    if kind == Cycle.KIND_REVIEW:
        return "Нужно резюме итогов"
    return "Нужно резюме: план и следующие шаги"


def _outcome_recorded(cycle):
    if cycle.kind == Cycle.KIND_RETRO:
        try:
            plan = cycle.retro_record.plan
        except RetroRecord.DoesNotExist:
            return False
        return bool(plan and plan.strip())
    if cycle.kind not in (Cycle.KIND_SURVEY, Cycle.KIND_REVIEW):
        return False
    try:
        text = cycle.summary.text
    except CycleSummary.DoesNotExist:
        return False
    return bool(text and text.strip())
