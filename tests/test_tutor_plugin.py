# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Smoke tests for the Tutor plugin's hook registrations.

We can't run Tutor itself in-process easily, but we can verify the
plugin module loads and registers the right filters and that the
init task command targets the in-container CLI (not the host wrapper).
"""

from tutor import hooks


def test_tutor_plugin_imports_and_registers():
    # Importing the module triggers the hooks.Filters.*.add_item calls.
    import tutorcourseinventory.plugin  # noqa: F401

    defaults = dict(hooks.Filters.CONFIG_DEFAULTS.iterate())
    assert "COURSE_INVENTORY_VERSION" in defaults
    assert defaults["COURSE_INVENTORY_PIP_SPEC"].startswith("course-inventory==")


def test_tutor_init_task_uses_in_container_cli():
    """Regression for M6: must NOT use the ./manage.py host wrapper."""
    import tutorcourseinventory.plugin  # noqa: F401

    tasks = list(hooks.Filters.CLI_DO_INIT_TASKS.iterate())
    ours = [(svc, cmd) for svc, cmd in tasks if "course_inventory" in cmd]
    assert ours, "init task not registered"
    for svc, cmd in ours:
        assert svc == "cms"
        assert cmd.startswith("python manage.py cms"), (
            f"command {cmd!r} must use the in-container CLI"
        )


def test_tutor_dockerfile_patch_pinned_to_config():
    """The pip install patch must interpolate COURSE_INVENTORY_PIP_SPEC."""
    import tutorcourseinventory.plugin  # noqa: F401

    patches = list(hooks.Filters.ENV_PATCHES.iterate())
    ours = [(name, body) for name, body in patches if "COURSE_INVENTORY_PIP_SPEC" in body]
    assert ours, "Dockerfile patch not registered"
    for name, body in ours:
        assert name == "openedx-dockerfile-post-python-requirements"
        assert "{{ COURSE_INVENTORY_PIP_SPEC }}" in body
