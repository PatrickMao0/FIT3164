# Generated by Django 4.2.20 on 2025-05-10 12:31

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("voting", "0006_userprofile"),
    ]

    operations = [
        migrations.RemoveField(model_name="election", name="status",),
        migrations.AlterUniqueTogether(
            name="candidate", unique_together={("club", "user")},
        ),
    ]
