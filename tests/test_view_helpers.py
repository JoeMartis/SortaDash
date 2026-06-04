# SPDX-License-Identifier: AGPL-3.0-or-later
"""Direct tests for the small view-layer helpers."""

import pytest
from django.core.paginator import Paginator

from course_inventory import services
from course_inventory.models import CourseTag
from course_inventory.views import _page_decorations, _sanitize_csv_cell

pytestmark = pytest.mark.django_db


def test_page_decorations_groups_owners_and_tags_per_course(
    make_course, add_role, staff_user, regular_user
):
    a = make_course("course-v1:edX+A+1")
    b = make_course("course-v1:edX+B+1")
    add_role(a, staff_user)
    add_role(a, regular_user, role="staff")
    add_role(b, staff_user)
    CourseTag.objects.create(course_id=a.id, key="lifecycle", value="active")

    page = Paginator(services.base_queryset().order_by("id"), 50).get_page(1)
    deco = _page_decorations(page)

    assert sorted(deco[a.id]["owners"]) == ["not-staff", "staff"]
    assert deco[b.id]["owners"] == ["staff"]
    assert [t.value for t in deco[a.id]["tags"]] == ["active"]
    assert deco[b.id]["tags"] == []


def test_page_decorations_does_not_mutate_course_instances(make_course):
    """
    Regression for M9: real CourseOverview is process-cached in
    edx-platform, so attaching per-request attrs to instances would
    leak across requests.
    """
    course = make_course("course-v1:edX+A+1")
    page = Paginator(services.base_queryset().order_by("id"), 50).get_page(1)
    _page_decorations(page)
    fetched = page.object_list[0]
    assert not hasattr(fetched, "owner_usernames")
    assert not hasattr(fetched, "tags")
    # The course argument should also be untouched.
    assert not hasattr(course, "owner_usernames")


def test_sanitize_csv_cell_defangs_formula_prefixes():
    for bad in ("=A1", "+1+1", "-2+3", "@cmd"):
        assert _sanitize_csv_cell(bad).startswith("'")
        assert _sanitize_csv_cell(bad)[1:] == bad


def test_sanitize_csv_cell_defangs_leading_whitespace_bypass():
    """Sheets strips leading whitespace/tab before evaluating formula."""
    for bad in (" =SUM(A1)", "\t=evil", "\r=evil", "  +1"):
        assert _sanitize_csv_cell(bad).startswith("'")
        assert _sanitize_csv_cell(bad)[1:] == bad


def test_sanitize_csv_cell_passes_through_safe_values():
    assert _sanitize_csv_cell("Intro to Biology") == "Intro to Biology"
    assert _sanitize_csv_cell("") == ""
    assert _sanitize_csv_cell(42) == 42
    assert _sanitize_csv_cell(None) is None
    # Leading whitespace alone is not a threat.
    assert _sanitize_csv_cell("   hello") == "   hello"
    assert _sanitize_csv_cell("\teval") == "\teval"
