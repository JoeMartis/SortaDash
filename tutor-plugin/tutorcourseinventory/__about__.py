# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Version of the Tutor companion plugin.

Pinned to the main ``course-inventory`` package's version so the two
can never drift. When the main package's pyproject is bumped, the
Tutor plugin's pyproject must be bumped in lockstep — ``make check``
verifies this.
"""

try:
    from course_inventory import __version__
except ImportError:
    # `course-inventory` may not be installed when this module is
    # imported (e.g. inside the Tutor host before the openedx image
    # has been rebuilt). Fall back to the pyproject string.
    __version__ = "0.1.0"
