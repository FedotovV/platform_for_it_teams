import uuid

from django.db import models


class Problem(models.Model):
    SOURCE_SURVEY = "survey"
    SOURCE_REVIEW = "review"
    SOURCE_MANUAL = "manual"
    SOURCE_RETRO = "retro"
    SOURCES = (
        (SOURCE_SURVEY, "опрос"),
        (SOURCE_REVIEW, "ревью"),
        (SOURCE_MANUAL, "ручное опасение"),
        (SOURCE_RETRO, "ретроспектива"),
    )

    STATUS_RAISED = "raised"
    STATUS_DISCUSSING = "discussing"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CLOSED = "closed"
    STATUSES = (
        (STATUS_RAISED, "поднята"),
        (STATUS_DISCUSSING, "на обсуждении"),
        (STATUS_IN_PROGRESS, "в работе"),
        (STATUS_CLOSED, "закрыта"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team_id = models.UUIDField()
    text = models.TextField("текст")
    source = models.CharField("источник", max_length=16, choices=SOURCES)
    for_discussion = models.BooleanField("к обсуждению", default=False)
    status = models.CharField(
        "статус",
        max_length=16,
        choices=STATUSES,
        default=STATUS_RAISED,
    )
    anonymous = models.BooleanField("анонимно", default=False)
    author_id = models.UUIDField()

    class Meta:
        verbose_name = "проблема"
        verbose_name_plural = "проблемы"


class ProblemCycleLink(models.Model):
    KIND_RAISED = "raised"
    KIND_CARRIED = "carried"
    KINDS = (
        (KIND_RAISED, "поднята в цикле"),
        (KIND_CARRIED, "перенесена в цикл"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="links")
    cycle_id = models.UUIDField()
    kind = models.CharField("вид связи", max_length=16, choices=KINDS)

    class Meta:
        verbose_name = "связь проблемы с циклом"
        verbose_name_plural = "связи проблем с циклами"
        constraints = [
            models.UniqueConstraint(
                fields=["problem", "cycle_id", "kind"],
                name="unique_problem_cycle_link",
            ),
        ]


class Action(models.Model):
    STATUS_ASSIGNED = "assigned"
    STATUS_DOING = "doing"
    STATUS_DONE = "done"
    STATUS_NOT_DONE = "not_done"
    STATUSES = (
        (STATUS_ASSIGNED, "назначено"),
        (STATUS_DOING, "делается"),
        (STATUS_DONE, "сделано"),
        (STATUS_NOT_DONE, "не сделано"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="actions")
    owner_id = models.UUIDField()
    due_at = models.DateTimeField("срок", null=True, blank=True)
    status = models.CharField(
        "статус",
        max_length=16,
        choices=STATUSES,
        default=STATUS_ASSIGNED,
    )

    class Meta:
        verbose_name = "действие"
        verbose_name_plural = "действия"
