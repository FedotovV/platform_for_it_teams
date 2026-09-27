import uuid

from django.db import models


class SurveySnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle_id = models.UUIDField(unique=True)
    scale_version = models.CharField("версия шкалы", max_length=64, null=True, blank=True)
    scale_maximum = models.FloatField("максимум баллов", null=True, blank=True)
    blocks = models.JSONField("баллы блоков", default=list)

    class Meta:
        verbose_name = "снимок опроса"
        verbose_name_plural = "снимки опросов"


class ColorBound(models.Model):
    """Абсолютные границы. Строк нет: сектор красится от доли максимума шкалы."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=64)
    min_score = models.FloatField()
    max_score = models.FloatField()

    class Meta:
        verbose_name = "граница цвета"
        verbose_name_plural = "границы цветов"
