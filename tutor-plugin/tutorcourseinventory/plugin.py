"""
Tutor plugin for the course-inventory CMS plugin.

Adds the `course-inventory` pip package to the openedx image and wires
its migrations into `tutor … do init` so operators don't need to run
them manually.
"""
from __future__ import annotations

from tutor import hooks

from .__about__ import __version__


hooks.Filters.CONFIG_DEFAULTS.add_items([
    ("COURSE_INVENTORY_VERSION", __version__),
    ("COURSE_INVENTORY_PIP_SPEC", f"course-inventory=={__version__}"),
])

# Install the CMS plugin package into the openedx image at build time.
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-dockerfile-post-python-requirements",
        "RUN pip install '{{ COURSE_INVENTORY_PIP_SPEC }}'",
    )
)

# Run the plugin's migrations during `tutor … do init`.
hooks.Filters.CLI_DO_INIT_TASKS.add_item(
    (
        "cms",
        "./manage.py cms migrate course_inventory",
    )
)
