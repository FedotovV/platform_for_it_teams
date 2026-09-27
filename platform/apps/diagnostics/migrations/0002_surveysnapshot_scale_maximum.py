from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("diagnostics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveysnapshot",
            name="scale_maximum",
            field=models.FloatField(blank=True, null=True, verbose_name="максимум баллов"),
        ),
    ]
