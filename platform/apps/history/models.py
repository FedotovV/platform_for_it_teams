import uuid

from django.db import models


class StatusAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.CharField(max_length=16)
    object_id = models.UUIDField()
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_id = models.UUIDField()
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "смена статуса"
        verbose_name_plural = "смены статусов"
        ordering = ["at", "id"]


class Attachment(models.Model):
    TARGET_PROBLEM = "problem"
    TARGET_ACTION = "action"
    TARGET_CYCLE = "cycle"
    TARGETS = (
        (TARGET_PROBLEM, "проблема"),
        (TARGET_ACTION, "действие"),
        (TARGET_CYCLE, "цикл"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_kind = models.CharField(max_length=16, choices=TARGETS)
    target_id = models.UUIDField()
    filename = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=64)
    uploaded_by = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "вложение"
        verbose_name_plural = "вложения"
