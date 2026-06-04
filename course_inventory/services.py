# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Single source of truth for the course inventory listing query.

Reads from existing edx-platform models only — never the modulestore.
Public surface:

- :func:`base_queryset` — annotated CourseOverview queryset.
- :func:`owners_for` / :func:`tags_for` — per-page decorators.
- :func:`distinct_orgs` / :func:`distinct_tag_values` — facet helpers.

All callers should go through ``base_queryset`` so the annotation
contract (``enrollment_count``, ``owner_count``, ``has_owner``) stays
in one place.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.db.models import (
    BooleanField,
    Count,
    ExpressionWrapper,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
)
from django.db.models.functions import Coalesce

from .models import CourseTag

# Roles in `CourseAccessRole` that count as "owning" a course for the
# purpose of the inventory's owner / orphan facet. Kept module-level so
# the test suite and downstream forks can override without monkeying
# with strings spread across the file.
OWNER_ROLES: tuple[str, ...] = ("instructor", "staff")


def _lazy_imports():
    """
    Import edx-platform models lazily so this package is importable in a
    plain Django environment (e.g. for `makemigrations --check`) without
    edx-platform present.
    """
    from common.djangoapps.student.models import (  # noqa: WPS433
        CourseAccessRole,
        CourseEnrollment,
    )
    from openedx.core.djangoapps.content.course_overviews.models import (  # noqa: WPS433
        CourseOverview,
    )

    return CourseOverview, CourseEnrollment, CourseAccessRole


def base_queryset() -> QuerySet:
    """
    Return an annotated ``CourseOverview`` queryset.

    Annotations on every row:

    - ``enrollment_count`` — count of active enrollments (int).
    - ``owner_count`` — count of staff/instructor roles (int).
    - ``has_owner`` — convenience boolean equivalent to
      ``owner_count > 0``.

    Implementation: one SELECT against ``course_overviews_courseoverview``
    plus two correlated subqueries; never joins enrollment or role
    rows directly, so the row count is always exactly the course count.
    """
    CourseOverview, CourseEnrollment, CourseAccessRole = _lazy_imports()

    enrollment_count = (
        CourseEnrollment.objects.filter(
            course_id=OuterRef("id"),
            is_active=True,
        )
        .order_by()
        .values("course_id")
        .annotate(c=Count("*"))
        .values("c")
    )

    owner_count = (
        CourseAccessRole.objects.filter(
            course_id=OuterRef("id"),
            role__in=OWNER_ROLES,
        )
        .order_by()
        .values("course_id")
        .annotate(c=Count("*"))
        .values("c")
    )

    return (
        CourseOverview.objects.all()
        .annotate(
            enrollment_count=Coalesce(Subquery(enrollment_count), 0),
            owner_count=Coalesce(Subquery(owner_count), 0),
        )
        .annotate(
            has_owner=ExpressionWrapper(
                Q(owner_count__gt=0),
                output_field=BooleanField(),
            ),
        )
    )


def owners_for(course_ids: Iterable) -> dict[object, list[str]]:
    """
    Return ``{course_id: [username, ...]}`` for the given course ids in
    a single query. Called once per page by the view, not per row.
    """
    _co, _ce, CourseAccessRole = _lazy_imports()
    rows = (
        CourseAccessRole.objects.filter(
            course_id__in=list(course_ids),
            role__in=OWNER_ROLES,
        )
        .select_related("user")
        .values_list("course_id", "user__username")
    )
    out: dict[object, list[str]] = {}
    for course_id, username in rows:
        out.setdefault(course_id, []).append(username)
    return out


def tags_for(course_ids: Iterable) -> dict[object, list[CourseTag]]:
    """``{course_id: [CourseTag, ...]}`` for the given course ids."""
    rows = CourseTag.objects.filter(course_id__in=list(course_ids))
    out: dict[object, list[CourseTag]] = {}
    for tag in rows:
        out.setdefault(tag.course_id, []).append(tag)
    return out


def distinct_orgs() -> list[str]:
    """Distinct org strings across all courses, alphabetically."""
    CourseOverview, _ce, _car = _lazy_imports()
    return list(CourseOverview.objects.order_by("org").values_list("org", flat=True).distinct())


def distinct_tag_values() -> list[tuple[str, str, int]]:
    """``[(key, value, count), ...]`` for the facet panel, sorted."""
    rows = CourseTag.objects.values("key", "value").annotate(c=Count("*")).order_by("key", "value")
    return [(r["key"], r["value"], r["c"]) for r in rows]
