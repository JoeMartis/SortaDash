"""
pytest config.

pyproject's `[tool.pytest.ini_options].pythonpath` already adds tests/
and the repo root to sys.path, so `import course_inventory`,
`import stubs`, and the `openedx.*` / `common.*` namespace shims all
resolve naturally. This file only holds shared fixtures.
"""

from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey
from stubs.models import CourseAccessRole, CourseEnrollment, CourseOverview


@pytest.fixture
def staff_user(db):
    User = get_user_model()
    return User.objects.create_user(username="staff", password="x", is_staff=True)


@pytest.fixture
def regular_user(db):
    User = get_user_model()
    return User.objects.create_user(username="not-staff", password="x")


@pytest.fixture
def make_course(db):
    """Factory for CourseOverview rows. Returns the saved instance."""
    now = datetime(2026, 1, 1, tzinfo=UTC)

    def _make(
        course_id,
        *,
        display_name="Course",
        org="edX",
        self_paced=False,
        catalog_visibility="both",
        modified=None,
        start=None,
        end=None,
    ):
        return CourseOverview.objects.create(
            id=CourseKey.from_string(course_id),
            display_name=display_name,
            org=org,
            self_paced=self_paced,
            catalog_visibility=catalog_visibility,
            modified=modified or now,
            start=start,
            end=end,
        )

    return _make


@pytest.fixture
def enroll(db):
    def _enroll(course, user, *, is_active=True):
        return CourseEnrollment.objects.create(course_id=course.id, user=user, is_active=is_active)

    return _enroll


@pytest.fixture
def add_role(db):
    def _add(course, user, role="instructor"):
        return CourseAccessRole.objects.create(course_id=course.id, user=user, role=role)

    return _add


@pytest.fixture
def old_modified():
    return datetime(2020, 1, 1, tzinfo=UTC)


@pytest.fixture
def recent_modified():
    return datetime.now(tz=UTC) - timedelta(days=1)
