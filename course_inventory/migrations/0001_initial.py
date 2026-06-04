from django.conf import settings
from django.db import migrations, models
import opaque_keys.edx.django.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseTag",
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
                (
                    "course_id",
                    opaque_keys.edx.django.models.CourseKeyField(
                        db_index=True, max_length=255
                    ),
                ),
                ("key", models.CharField(db_index=True, max_length=64)),
                ("value", models.CharField(db_index=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("key", "value"),
                "unique_together": {("course_id", "key", "value")},
            },
        ),
        migrations.AddIndex(
            model_name="coursetag",
            index=models.Index(
                fields=["key", "value"],
                name="course_inve_key_61badc_idx",
            ),
        ),
        migrations.CreateModel(
            name="SavedView",
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
                ("name", models.CharField(max_length=128)),
                ("filters_json", models.JSONField(default=dict)),
                ("shared", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="course_inventory_saved_views",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("name",),
                "unique_together": {("owner", "name")},
            },
        ),
    ]
