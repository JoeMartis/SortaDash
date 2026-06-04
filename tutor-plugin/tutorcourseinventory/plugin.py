# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tutor plugin for the course-inventory CMS plugin.

Adds the `course-inventory` pip package to the openedx image and wires
its migrations into `tutor … do init` so operators don't need to run
them manually.
"""

from __future__ import annotations

from tutor import hooks

from .__about__ import __version__

# Default pip spec installed into the openedx image. Override via
# `tutor config save --set COURSE_INVENTORY_PIP_SPEC=...` to install
# from a fork, a local path, or a different version. The value is
# interpolated into a shell `pip install` command in the Dockerfile,
# so operators overriding it MUST supply a literal pip requirement —
# no shell metacharacters, no command chaining. We document this in
# the plugin README; we do not validate here because Tutor itself is
# operator-administered.
_DEFAULT_PIP_SPEC = f"course-inventory=={__version__}"

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        ("COURSE_INVENTORY_VERSION", __version__),
        ("COURSE_INVENTORY_PIP_SPEC", _DEFAULT_PIP_SPEC),
    ]
)

# Install the CMS plugin package into the openedx image at build time.
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-dockerfile-post-python-requirements",
        "RUN pip install '{{ COURSE_INVENTORY_PIP_SPEC }}'",
    )
)

# Run the plugin's migrations during `tutor … do init`. The command
# runs *inside* the openedx container, where the CLI is plain
# `python manage.py cms`, not the Tutor-host `./manage.py cms` wrapper.
hooks.Filters.CLI_DO_INIT_TASKS.add_item(
    (
        "cms",
        "python manage.py cms migrate course_inventory",
    )
)
