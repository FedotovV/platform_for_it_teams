import uuid

from django.db import models


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("название", max_length=255)

    class Meta:
        verbose_name = "организация"
        verbose_name_plural = "организации"

    def __str__(self):
        return self.name


class Person(models.Model):
    """Человек в одной организации. Учётная запись остаётся в identity."""

    user_id = models.UUIDField(unique=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="people",
    )

    class Meta:
        verbose_name = "человек"
        verbose_name_plural = "люди"

    def __str__(self):
        return str(self.user_id)


class OrgLeadership(models.Model):
    """Руководитель организации. Это не роль внутри команды."""

    user_id = models.UUIDField()
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leaders",
    )

    class Meta:
        verbose_name = "руководитель организации"
        verbose_name_plural = "руководители организаций"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "organization"],
                name="unique_org_leader",
            ),
        ]


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="teams",
    )
    name = models.CharField("название", max_length=255)

    class Meta:
        verbose_name = "команда"
        verbose_name_plural = "команды"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_MANAGER = "manager"
    ROLE_LEADER = "leader"
    ROLE_MEMBER = "member"
    ROLE_FACILITATOR = "facilitator"
    ROLES = (
        (ROLE_MANAGER, "менеджер"),
        (ROLE_LEADER, "лидер"),
        (ROLE_MEMBER, "участник"),
        (ROLE_FACILITATOR, "фасилитатор"),
    )

    user_id = models.UUIDField()
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField("роль", max_length=32, choices=ROLES)

    class Meta:
        verbose_name = "участие"
        verbose_name_plural = "участия"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "team"],
                name="unique_team_membership",
            ),
        ]


class SelectedTeam(models.Model):
    user_id = models.UUIDField(unique=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="selections")

    class Meta:
        verbose_name = "выбранная команда"
        verbose_name_plural = "выбранные команды"
