# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the plugin's CMS-side settings hook.

The hook is invoked by edx-platform's plugin loader; here we call it
manually against a stub settings module to verify the defaults and the
django_htmx INSTALLED_APPS shim.
"""

import types


def _stub_settings(**overrides):
    defaults = {"INSTALLED_APPS": ["django.contrib.auth"]}
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def test_plugin_settings_applies_defaults():
    from course_inventory.settings.common import plugin_settings

    s = _stub_settings()
    plugin_settings(s)
    assert s.COURSE_INVENTORY_PAGE_SIZE == 50
    assert s.COURSE_INVENTORY_EXPORT_CHUNK_SIZE == 500
    assert s.COURSE_INVENTORY_EXPORT_MAX_ROWS == 10_000
    assert s.COURSE_INVENTORY_TAG_KEYS == ["lifecycle", "team", "program", "term"]


def test_plugin_settings_respects_existing_overrides():
    from course_inventory.settings.common import plugin_settings

    s = _stub_settings(
        COURSE_INVENTORY_PAGE_SIZE=100,
        COURSE_INVENTORY_EXPORT_MAX_ROWS=42,
    )
    plugin_settings(s)
    assert s.COURSE_INVENTORY_PAGE_SIZE == 100
    assert s.COURSE_INVENTORY_EXPORT_MAX_ROWS == 42


def test_plugin_settings_adds_django_htmx_to_installed_apps():
    from course_inventory.settings.common import plugin_settings

    s = _stub_settings()
    plugin_settings(s)
    assert "django_htmx" in s.INSTALLED_APPS


def test_plugin_settings_does_not_duplicate_django_htmx():
    from course_inventory.settings.common import plugin_settings

    s = _stub_settings(
        INSTALLED_APPS=["django.contrib.auth", "django_htmx"],
    )
    plugin_settings(s)
    assert s.INSTALLED_APPS.count("django_htmx") == 1
