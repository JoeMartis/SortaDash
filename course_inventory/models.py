# SPDX-License-Identifier: AGPL-3.0-or-later
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
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

    course_id = CourseKeyField(max_length=255, db_index=True, verbose_name=_("course id"))
    key = models.CharField(max_length=64, db_index=True, verbose_name=_("key"))
    value = models.CharField(max_length=128, db_index=True, verbose_name=_("value"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("created by"),
    )

    class Meta:
        verbose_name = _("course tag")
        verbose_name_plural = _("course tags")
        unique_together = ("course_id", "key", "value")
        indexes = [models.Index(fields=["key", "value"])]
        ordering = ("key", "value")

    def __str__(self):
        return f"{self.course_id} {self.key}={self.value}"


class SavedView(models.Model):
    """A named filter combination over the course inventory."""

    name = models.CharField(max_length=128, verbose_name=_("name"))
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_inventory_saved_views",
        verbose_name=_("owner"),
    )
    filters_json = models.JSONField(default=dict, verbose_name=_("filters"))
    shared = models.BooleanField(default=False, verbose_name=_("shared"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("saved view")
        verbose_name_plural = _("saved views")
        unique_together = ("owner", "name")
        ordering = ("name",)

    def __str__(self):
        return self.name
