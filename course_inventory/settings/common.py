# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Plugin settings hook for course_inventory.

Loaded by edx-platform via the plugin_app config in apps.py. Adds the
plugin's defaults to the CMS settings module without requiring any edit
to edx-platform.
"""


def plugin_settings(settings):
    settings.COURSE_INVENTORY_PAGE_SIZE = getattr(settings, "COURSE_INVENTORY_PAGE_SIZE", 50)
    settings.COURSE_INVENTORY_EXPORT_CHUNK_SIZE = getattr(
        settings, "COURSE_INVENTORY_EXPORT_CHUNK_SIZE", 500
    )
    # Hard ceiling on how many rows the streaming export will emit.
    # Prevents an unfiltered export from streaming the entire catalog
    # under load. Operators can raise this if they really want it; the
    # default is generous enough for a 5K-course install.
    settings.COURSE_INVENTORY_EXPORT_MAX_ROWS = getattr(
        settings, "COURSE_INVENTORY_EXPORT_MAX_ROWS", 10_000
    )
    settings.COURSE_INVENTORY_TAG_KEYS = getattr(
        settings,
        "COURSE_INVENTORY_TAG_KEYS",
        ["lifecycle", "team", "program", "term"],
    )

    # Ensure django_htmx is installed so the bundled htmx.min.js asset
    # is served from the host's own origin (no CDN, CSP-friendly).
    if "django_htmx" not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ["django_htmx"]
