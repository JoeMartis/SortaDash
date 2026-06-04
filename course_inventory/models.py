from django.conf import settings
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField


class CourseTag(models.Model):
    """
    Operator-defined tag applied to a course.

    Tags are a *shared* organizing layer: any staff user can add or
    remove any tag on any course. This matches the design intent (an
    admin surface for organizing a catalog the whole staff team owns).
    ``created_by`` is recorded for audit only and is *not* enforced as
    an ownership boundary. Mutating actions are logged at INFO.
    """

    course_id = CourseKeyField(max_length=255, db_index=True)
    key = models.CharField(max_length=64, db_index=True)
    value = models.CharField(max_length=128, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        unique_together = ("course_id", "key", "value")
        indexes = [models.Index(fields=["key", "value"])]
        ordering = ("key", "value")

    def __str__(self):
        return f"{self.course_id} {self.key}={self.value}"


class SavedView(models.Model):
    name = models.CharField(max_length=128)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_inventory_saved_views",
    )
    filters_json = models.JSONField(default=dict)
    shared = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("owner", "name")
        ordering = ("name",)

    def __str__(self):
        return self.name
