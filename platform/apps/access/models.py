import uuid

from django.db import models


class TeamGrant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team_id = models.UUIDField()
    action = models.CharField("действие", max_length=64)
    role = models.CharField("роль", max_length=32)

    class Meta:
        verbose_name = "право команды"
        verbose_name_plural = "права команды"
        constraints = [
            models.UniqueConstraint(
                fields=["team_id", "action", "role"],
                name="unique_team_grant",
            ),
        ]
