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
    """
    Factory for CourseOverview rows.

    `modified` has ``auto_now=True`` on the real model (and on our stub
    as of round 3), so setting it via ``create()`` is a no-op: Django
    overwrites it on save. To get a course with a non-now ``modified``
    timestamp we have to ``.update()`` it after the row exists, which
    matches how production data ages naturally.
    """

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
        course = CourseOverview.objects.create(
            id=CourseKey.from_string(course_id),
            display_name=display_name,
            org=org,
            self_paced=self_paced,
            catalog_visibility=catalog_visibility,
            start=start,
            end=end,
        )
        if modified is not None:
            CourseOverview.objects.filter(pk=course.pk).update(modified=modified)
            course.refresh_from_db(fields=("modified",))
        return course

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
