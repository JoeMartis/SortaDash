"""
Single source of truth for the course inventory listing query.

Reads from existing edx-platform models only — never the modulestore.
"""

from django.db.models import (
    BooleanField,
    Count,
    ExpressionWrapper,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import Coalesce

from .models import CourseTag


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


OWNER_ROLES = ("instructor", "staff")


def base_queryset():
    """
    Return an annotated CourseOverview queryset suitable for the
    inventory list. One query plus subquery annotations — no joins that
    multiply rows.
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

    qs = (
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
    return qs


def owners_for(course_ids):
    """
    Return {course_id: [username, ...]} for the given course ids in a
    single query. Called once per page (not per row) by the view.
    """
    _, _, CourseAccessRole = _lazy_imports()
    rows = (
        CourseAccessRole.objects.filter(
            course_id__in=list(course_ids),
            role__in=OWNER_ROLES,
        )
        .select_related("user")
        .values_list("course_id", "user__username")
    )
    out = {}
    for course_id, username in rows:
        out.setdefault(course_id, []).append(username)
    return out


def tags_for(course_ids):
    """{course_id: [CourseTag, ...]} for the given course ids."""
    rows = CourseTag.objects.filter(course_id__in=list(course_ids))
    out = {}
    for tag in rows:
        out.setdefault(tag.course_id, []).append(tag)
    return out


def distinct_orgs():
    CourseOverview, _, _ = _lazy_imports()
    return list(CourseOverview.objects.order_by("org").values_list("org", flat=True).distinct())


def distinct_tag_values():
    """[(key, value, count), ...] for the facet panel."""
    rows = CourseTag.objects.values("key", "value").annotate(c=Count("*")).order_by("key", "value")
    return [(r["key"], r["value"], r["c"]) for r in rows]
