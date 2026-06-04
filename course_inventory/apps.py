from django.apps import AppConfig


class CourseInventoryConfig(AppConfig):
    name = "course_inventory"
    verbose_name = "Course Inventory"
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
