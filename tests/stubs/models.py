"""
Minimal stand-ins for the edx-platform models that course_inventory
reads. The fields we declare here are the strict subset that the
plugin's services + filters touch — enough to write meaningful tests
without dragging in real edx-platform code.
"""

from django.conf import settings
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField


class CourseOverview(models.Model):
    id = CourseKeyField(max_length=255, primary_key=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    org = models.CharField(max_length=255)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    self_paced = models.BooleanField(default=False)
    catalog_visibility = models.CharField(max_length=64, default="both")
    # Matches the real `CourseOverview.modified` field (which has
    # auto_now=True). Tests that need to control the value must use
    # `CourseOverview.objects.filter(...).update(modified=...)` AFTER
    # the initial save, mirroring how production data ages naturally.
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "stubs"


class CourseEnrollment(models.Model):
    course_id = CourseKeyField(max_length=255, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "stubs"


class CourseAccessRole(models.Model):
    course_id = CourseKeyField(max_length=255, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=64)

    class Meta:
        app_label = "stubs"
