import uuid
from pathlib import Path

from django.conf import settings

from apps.cycles.api import cycle_brief, cycles_for_team
from apps.diagnostics.api import snapshot_for
from apps.history.models import Attachment
from apps.problems.api import team_id_of_action, team_id_of_problem
from apps.teams.api import can_see_team

TARGETS = {code for code, _label in Attachment.TARGETS}


class HistoryError(Exception):
    def __init__(self, detail, status=400):
        self.detail = detail
        self.status = status


def object_team_id(kind, object_id):
    if kind == Attachment.TARGET_CYCLE:
        brief = cycle_brief(object_id)
        if brief is None:
            return None
        return brief["team_id"]
    if kind == Attachment.TARGET_PROBLEM:
        return team_id_of_problem(object_id)
    if kind == Attachment.TARGET_ACTION:
        return team_id_of_action(object_id)
    return None


def team_history(user_id, team_id):
    if not can_see_team(user_id, team_id):
        raise HistoryError("Команда не найдена", status=404)
    cycles = []
    for row in cycles_for_team(team_id):
        snapshot = snapshot_for(row["id"], with_color=False) if row["kind"] == "survey" else None
        cycles.append(
            {
                "id": str(row["id"]),
                "kind": row["kind"],
                "status": row["status"],
                "scheduled_at": None if row["scheduled_at"] is None else row["scheduled_at"].isoformat(),
                "closed_at": None if row["closed_at"] is None else row["closed_at"].isoformat(),
                "snapshot": snapshot,
            }
        )
    return cycles


def store_attachment(user_id, target_kind, target_id, upload):
    if target_kind not in TARGETS:
        raise HistoryError("Вложение можно добавить только к проблеме, действию или циклу")
    team_id = object_team_id(target_kind, target_id)
    if team_id is None or not can_see_team(user_id, team_id):
        raise HistoryError("Объект не найден", status=404)
    filename = Path(getattr(upload, "name", "") or "").name
    if not filename or filename in {".", ".."}:
        raise HistoryError("Нужен файл")
    stored_name = uuid.uuid4().hex
    root = Path(settings.ATTACHMENT_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    path = root / stored_name
    with path.open("wb") as handle:
        for chunk in upload.chunks():
            handle.write(chunk)
    return Attachment.objects.create(
        target_kind=target_kind,
        target_id=target_id,
        filename=filename[:255],
        stored_name=stored_name,
        uploaded_by=user_id,
    )


def open_attachment(user_id, attachment_id):
    row = Attachment.objects.filter(pk=attachment_id).first()
    if row is None:
        raise HistoryError("Вложение не найдено", status=404)
    team_id = object_team_id(row.target_kind, row.target_id)
    if team_id is None or not can_see_team(user_id, team_id):
        raise HistoryError("Вложение не найдено", status=404)
    path = Path(settings.ATTACHMENT_ROOT) / row.stored_name
    if not path.is_file():
        raise HistoryError("Вложение не найдено", status=404)
    return row, path
