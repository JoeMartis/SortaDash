"""
Plugin settings hook for course_inventory.

Loaded by edx-platform via the plugin_app config in apps.py. Adds the
plugin's defaults to the CMS settings module without requiring any edit
to edx-platform.
"""


def plugin_settings(settings):
    settings.COURSE_INVENTORY_PAGE_SIZE = getattr(
        settings, "COURSE_INVENTORY_PAGE_SIZE", 50
    )
    settings.COURSE_INVENTORY_EXPORT_CHUNK_SIZE = getattr(
        settings, "COURSE_INVENTORY_EXPORT_CHUNK_SIZE", 500
    )
    settings.COURSE_INVENTORY_TAG_KEYS = getattr(
        settings,
        "COURSE_INVENTORY_TAG_KEYS",
        ["lifecycle", "team", "program", "term"],
    )
