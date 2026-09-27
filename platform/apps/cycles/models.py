import uuid

from django.db import models


class Cycle(models.Model):
    KIND_SURVEY = "survey"
    KIND_REVIEW = "review"
    KIND_RETRO = "retro"
    KINDS = (
        (KIND_SURVEY, "опрос"),
        (KIND_REVIEW, "ревью"),
        (KIND_RETRO, "ретро"),
    )

    STATUS_DRAFT = "draft"
    STATUS_COLLECT = "collect"
    STATUS_REVIEW = "review"
    STATUS_CLOSED = "closed"
    STATUSES = (
        (STATUS_DRAFT, "черновик"),
        (STATUS_COLLECT, "сбор"),
        (STATUS_REVIEW, "разбор"),
        (STATUS_CLOSED, "закрыт"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team_id = models.UUIDField()
    kind = models.CharField("вид", max_length=16, choices=KINDS)
    status = models.CharField(
        "статус",
        max_length=16,
        choices=STATUSES,
        default=STATUS_DRAFT,
    )
    scheduled_at = models.DateTimeField("дата и время", null=True, blank=True)
    closed_at = models.DateTimeField("закрыт в", null=True, blank=True)
    closed_by = models.UUIDField("закрыл", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "цикл"
        verbose_name_plural = "циклы"
        ordering = ["created_at", "id"]


class CycleSummary(models.Model):
    cycle = models.OneToOneField(Cycle, on_delete=models.CASCADE, related_name="summary")
    text = models.TextField("резюме", blank=True)

    class Meta:
        verbose_name = "резюме цикла"
        verbose_name_plural = "резюме циклов"


class TeamSurveySettings(models.Model):
    QUARTER_MONTHS = 3

    team_id = models.UUIDField(unique=True)
    interval_months = models.PositiveSmallIntegerField(default=QUARTER_MONTHS)

    class Meta:
        verbose_name = "интервал опроса"
        verbose_name_plural = "интервалы опросов"


class ReviewNotes(models.Model):
    cycle = models.OneToOneField(Cycle, on_delete=models.CASCADE, related_name="review_notes")
    plan_and_fact = models.TextField("план и факт", blank=True)
    results = models.TextField("результаты", blank=True)
    deviation_causes = models.TextField("причины отклонений", blank=True)
    changes = models.TextField("что изменяем", blank=True)
    stops = models.TextField("что перестаём делать", blank=True)
    reinforces = models.TextField("что усиливаем", blank=True)

    class Meta:
        verbose_name = "заметки ревью"
        verbose_name_plural = "заметки ревью"


class RetroRecord(models.Model):
    cycle = models.OneToOneField(Cycle, on_delete=models.CASCADE, related_name="retro_record")
    plan = models.TextField("план", blank=True)
    artifacts = models.JSONField("артефакты", default=list, blank=True)

    class Meta:
        verbose_name = "запись ретро"
        verbose_name_plural = "записи ретро"
