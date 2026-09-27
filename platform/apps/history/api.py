from apps.history.models import StatusAudit

ENTITIES = {"cycle", "problem", "action"}


def record_status_change(entity, object_id, from_status, to_status, actor_id):
    """Список смен статусов. Полный журнал правок здесь не ведётся."""
    if entity not in ENTITIES or from_status == to_status:
        return None
    return StatusAudit.objects.create(
        entity=entity,
        object_id=object_id,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
    )


def changes_for(entity, object_id):
    rows = StatusAudit.objects.filter(entity=entity, object_id=object_id).order_by("at", "id")
    return [
        {
            "entity": row.entity,
            "object_id": str(row.object_id),
            "from_status": row.from_status,
            "to_status": row.to_status,
            "actor_id": str(row.actor_id),
            "at": row.at.isoformat(),
        }
        for row in rows
    ]
