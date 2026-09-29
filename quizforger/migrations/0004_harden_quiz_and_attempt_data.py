from django.db import migrations, models


def clean_invalid_attempts(apps, schema_editor):
    Attempt = apps.get_model("quizforger", "Attempt")
    Attempt.objects.filter(total__lte=0).delete()
    Attempt.objects.filter(score__lt=0).update(score=0)
    Attempt.objects.filter(score__gt=models.F("total")).update(score=models.F("total"))


class Migration(migrations.Migration):

    dependencies = [
        ("quizforger", "0003_userpreference"),
    ]

    operations = [
        migrations.RunPython(clean_invalid_attempts, migrations.RunPython.noop),
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
