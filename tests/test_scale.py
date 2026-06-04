# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Scale + query-budget tests.

The design doc promises the dashboard stays fast at 400+ courses on a
single ``CourseOverview`` SELECT plus correlated subqueries. We
verify that promise here by populating a non-trivial fixture and
counting queries — *not* by timing, which is too flaky to gate CI on.

If a future change introduces an N+1 or a per-row query, the query-
count budget breaks and these tests fail loudly.
"""

from __future__ import annotations

import pytest
from django.core.paginator import Paginator
from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from stubs.models import CourseAccessRole, CourseEnrollment, CourseOverview

from course_inventory import services
from course_inventory.models import CourseTag
from course_inventory.views import _page_decorations

pytestmark = pytest.mark.django_db

NUM_COURSES = 1_000


@pytest.fixture
def large_catalog(db, django_user_model):
    """
    Seed a realistic-ish catalog: 1,000 courses, ~200 with owners,
    ~100 enrolled-against, ~50 tagged. One time setup per test that
    requests it.

    Uses ``bulk_create`` so seeding doesn't dominate the test runtime.
    """
    owners = [
        django_user_model.objects.create_user(username=f"owner_{i}", password="x") for i in range(5)
    ]
    students = [
        django_user_model.objects.create_user(username=f"student_{i}", password="x")
        for i in range(20)
    ]

    courses = [
        CourseOverview(
            id=CourseKey.from_string(f"course-v1:edX+S{i:04d}+1"),
            display_name=f"Course {i}",
            org="edX" if i % 3 == 0 else "MITx" if i % 3 == 1 else "Stanford",
            self_paced=bool(i % 2),
            catalog_visibility="both",
        )
        for i in range(NUM_COURSES)
    ]
    CourseOverview.objects.bulk_create(courses)

    # Owners on every 5th course.
    roles = [
        CourseAccessRole(course_id=courses[i].id, user=owners[i % len(owners)], role="instructor")
        for i in range(0, NUM_COURSES, 5)
    ]
    CourseAccessRole.objects.bulk_create(roles)

    # Enrollments spread across the first 100 courses, 5 per course.
    enrollments = [
        CourseEnrollment(
            course_id=courses[i].id,
            user=students[j % len(students)],
            is_active=True,
        )
        for i in range(100)
        for j in range(5)
    ]
    CourseEnrollment.objects.bulk_create(enrollments)

    # Tags on every 20th course.
    tags = [
        CourseTag(
            course_id=courses[i].id,
            key="lifecycle",
            value="active" if i % 40 else "archived",
        )
        for i in range(0, NUM_COURSES, 20)
    ]
    CourseTag.objects.bulk_create(tags)

    return courses


def test_base_queryset_stays_one_select_at_scale(large_catalog, settings):
    """
    ``base_queryset()`` should evaluate to a single SELECT against
    ``course_overviews_courseoverview`` regardless of catalog size.
    """
    settings.DEBUG = True  # so CaptureQueriesContext sees queries
    reset_queries()
    qs = services.base_queryset()

    with CaptureQueriesContext(connection) as ctx:
        list(qs.order_by("id")[:50])

    # One SELECT for the page; correlated subqueries are inline.
    assert len(ctx.captured_queries) == 1, [q["sql"] for q in ctx.captured_queries]


def test_full_page_render_query_budget(large_catalog, client, settings):
    """
    Hitting ``/course-inventory/`` against a 1000-course catalog
    must stay within a small constant query budget. Today the budget
    is 12 — generous enough to absorb auth/session machinery and the
    facet helpers, tight enough that any N+1 in the listing view
    will trip it.
    """
    from django.contrib.auth import get_user_model

    staff = get_user_model().objects.create_user(
        username="staff_scale", password="x", is_staff=True
    )
    client.force_login(staff)

    settings.DEBUG = True
    reset_queries()
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(reverse("course_inventory:inventory"))
    assert response.status_code == 200

    # Filter out Django session / auth bookkeeping queries — we
    # only care about the plugin's own query count.
    plugin_queries = [
        q
        for q in ctx.captured_queries
        if any(
            tbl in q["sql"]
            for tbl in (
                "course_inventory_",
                "stubs_courseoverview",
                "stubs_courseenrollment",
                "stubs_courseaccessrole",
            )
        )
    ]
    # Hot-path queries: paginator COUNT + page SELECT, owners SELECT,
    # tags SELECT, distinct_orgs SELECT, distinct_tag_values SELECT,
    # _visible_saved_views SELECT — six queries, plus the
    # _visible_saved_views existence check the facet panel makes.
    # Allow up to 8 to leave headroom; assert no N+1.
    assert len(plugin_queries) <= 8, (
        f"plugin query count {len(plugin_queries)} exceeds budget; "
        f"queries: {[q['sql'][:80] for q in plugin_queries]}"
    )


def test_page_decorations_two_queries_regardless_of_size(large_catalog):
    """
    ``_page_decorations(page)`` is supposed to be exactly two queries
    (owners + tags) regardless of page size — verifying no N+1 hides
    inside the helper.
    """
    page = Paginator(services.base_queryset().order_by("id"), 50).get_page(1)
    # Force evaluation of the page itself before measuring.
    list(page.object_list)

    with CaptureQueriesContext(connection) as ctx:
        deco = _page_decorations(page)

    assert len(ctx.captured_queries) == 2, [q["sql"] for q in ctx.captured_queries]
    # Sanity check on the result shape.
    assert len(deco) == 50


def test_filtered_listing_stays_one_select(large_catalog, settings):
    """
    Applying every filter shape ought not multiply queries.
    """
    from django.http import QueryDict

    from course_inventory import filters

    parsed = filters.parse(
        QueryDict("q=Course&org=edX&pacing=self&enrollment=0&has_owner=yes&sort=modified&dir=desc")
    )
    qs = filters.apply(services.base_queryset(), parsed)

    settings.DEBUG = True
    with CaptureQueriesContext(connection) as ctx:
        list(qs[:50])
    assert len(ctx.captured_queries) == 1
