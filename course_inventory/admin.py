# SPDX-License-Identifier: AGPL-3.0-or-later
from django.contrib import admin

from .models import CourseTag, SavedView


@admin.register(CourseTag)
class CourseTagAdmin(admin.ModelAdmin):
    list_display = ("course_id", "key", "value", "created_at")
    list_filter = ("key",)
    search_fields = ("course_id", "key", "value")


@admin.register(SavedView)
class SavedViewAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "shared", "updated_at")
    list_filter = ("shared",)
    search_fields = ("name", "owner__username")
