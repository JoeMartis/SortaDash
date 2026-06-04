# SPDX-License-Identifier: AGPL-3.0-or-later
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CourseInventoryConfig(AppConfig):
    name = "course_inventory"
    verbose_name = _("Course Inventory")
    default_auto_field = "django.db.models.BigAutoField"

    plugin_app = {
        "url_config": {
            "cms.djangoapp": {
                "namespace": "course_inventory",
                "regex": r"^course-inventory/",
                "relative_path": "urls",
            },
        },
        "settings_config": {
            "cms.djangoapp": {
                "common": {"relative_path": "settings.common"},
            },
        },
    }
