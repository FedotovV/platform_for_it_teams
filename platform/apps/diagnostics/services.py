from apps.access.api import ADVANCE_CYCLE, can
from apps.cycles.api import KIND_SURVEY, cycle_brief
from apps.diagnostics.models import SurveySnapshot
from apps.teams.api import can_see_team


class DiagnosticError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status


def record_snapshot(user_id, cycle_id, scale_version, blocks, scale_maximum=None):
    brief = cycle_brief(cycle_id)
    if brief is None or not can_see_team(user_id, brief["team_id"]):
        raise DiagnosticError("Цикл не найден", status=404)
    if brief["kind"] != KIND_SURVEY:
        raise DiagnosticError("Снимок пишется только на опрос")
    if not can(user_id, brief["team_id"], ADVANCE_CYCLE):
        raise DiagnosticError("Недостаточно прав", status=403)
    cleaned = _blocks(blocks)
    version = scale_version
    if version is not None:
        if not isinstance(version, str):
            raise DiagnosticError("Версия шкалы — текст или пусто")
        version = version.strip() or None
    row, _created = SurveySnapshot.objects.update_or_create(
        cycle_id=cycle_id,
        defaults={
            "scale_version": version,
            "scale_maximum": _maximum(scale_maximum),
            "blocks": cleaned,
        },
    )
    return row


def _blocks(blocks):
    if not isinstance(blocks, list) or not blocks:
        raise DiagnosticError("Нужны баллы блоков")
    cleaned = []
    for item in blocks:
        if not isinstance(item, dict):
            raise DiagnosticError("Блок — код и балл")
        code = item.get("code")
        score = item.get("score")
        if not isinstance(code, str) or not code.strip():
            raise DiagnosticError("Нужен код блока")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise DiagnosticError("Балл блока — число")
        cleaned.append({"code": code.strip(), "score": score})
    return cleaned


def _maximum(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if text == "":
            return None
        try:
            value = float(text) if "." in text else int(text)
        except ValueError:
            raise DiagnosticError("Максимум шкалы — число")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiagnosticError("Максимум шкалы — число")
    if value <= 0:
        raise DiagnosticError("Максимум шкалы — число больше нуля")
    return value
