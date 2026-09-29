from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quizforger", "0003_userpreference"),
    ]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attempt",
            name="submission_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="quiz",
            index=models.Index(
                fields=["archived_at", "-created_at"],
                name="quiz_active_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="attempt",
            constraint=models.CheckConstraint(
                condition=models.Q(("total__gt", 0)),
                name="attempt_total_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="attempt",
            constraint=models.CheckConstraint(
                condition=models.Q(("score__lte", models.F("total"))),
                name="attempt_score_lte_total",
            ),
        ),
        migrations.AddConstraint(
            model_name="attempt",
            constraint=models.UniqueConstraint(
                condition=models.Q(("submission_id__isnull", False)),
                fields=("quiz", "submission_id"),
                name="attempt_unique_submission_per_quiz",
            ),
        ),
    ]
