# Generated by Django 4.2.20 on 2025-03-26 11:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("voting", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Club",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.RemoveField(model_name="candidate", name="name",),
        migrations.AddField(
            model_name="candidate",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="candidates/"),
        ),
        migrations.AddField(
            model_name="candidate",
            name="user",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="candidate_entries",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="election",
            name="created_by",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="created_elections",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="election",
            name="status",
            field=models.CharField(
                choices=[
                    ("Pending", "Pending"),
                    ("Ongoing", "Ongoing"),
                    ("Ended", "Ended"),
                ],
                default="Pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vote",
            name="voter",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="votes_cast",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="election",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="election", name="end_date", field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="election", name="start_date", field=models.DateTimeField(),
        ),
        migrations.AddField(
            model_name="election",
            name="club",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="elections",
                to="voting.club",
            ),
            preserve_default=False,
        ),
    ]
