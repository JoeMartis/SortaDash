# SPDX-License-Identifier: AGPL-3.0-or-later
from django.urls import path

from . import views

app_name = "course_inventory"

urlpatterns = [
    path("", views.inventory_list, name="inventory"),
    path("export", views.export, name="export"),
    path("tag/<path:course_key>", views.tag_edit, name="tag_edit"),
    path("views/", views.saved_view_list, name="saved_view_list"),
    path("views/new", views.saved_view_create, name="saved_view_create"),
    path(
        "views/<int:pk>/delete",
        views.saved_view_delete,
        name="saved_view_delete",
    ),
]
