import pytest

from course_inventory import services

pytestmark = pytest.mark.django_db


def test_base_queryset_annotates_zero_when_no_enrollments_or_roles(make_course):
    course = make_course("course-v1:edX+A+1")
    row = services.base_queryset().get(id=course.id)
    assert row.enrollment_count == 0
    assert row.owner_count == 0


def test_base_queryset_counts_only_active_enrollments(
    make_course, enroll, staff_user, regular_user
):
    course = make_course("course-v1:edX+A+1")
    enroll(course, staff_user, is_active=True)
    enroll(course, regular_user, is_active=False)  # inactive: excluded
    row = services.base_queryset().get(id=course.id)
    assert row.enrollment_count == 1


def test_base_queryset_owner_count_only_counts_owner_roles(make_course, add_role, staff_user):
    course = make_course("course-v1:edX+A+1")
    add_role(course, staff_user, role="instructor")
    add_role(course, staff_user, role="data_researcher")  # not an owner role
    row = services.base_queryset().get(id=course.id)
    assert row.owner_count == 1


def test_owners_for_groups_by_course(make_course, add_role, staff_user, regular_user):
    a = make_course("course-v1:edX+A+1")
    b = make_course("course-v1:edX+B+1")
    add_role(a, staff_user)
    add_role(a, regular_user, role="staff")
    add_role(b, staff_user)
    owners = services.owners_for([a.id, b.id])
    assert sorted(owners[a.id]) == ["not-staff", "staff"]
    assert owners[b.id] == ["staff"]


def test_distinct_tag_values_returns_counts(make_course):
    """Each (key,value) appears once with its course count."""
    from course_inventory.models import CourseTag

    a = make_course("course-v1:edX+A+1")
    b = make_course("course-v1:edX+B+1")
    CourseTag.objects.create(course_id=a.id, key="lifecycle", value="active")
    CourseTag.objects.create(course_id=b.id, key="lifecycle", value="active")
    CourseTag.objects.create(course_id=a.id, key="team", value="x")
    result = services.distinct_tag_values()
    assert ("lifecycle", "active", 2) in result
    assert ("team", "x", 1) in result
    # Sorted by (key, value).
    assert result == sorted(result)


def test_distinct_tag_values_empty():
    assert services.distinct_tag_values() == []


def test_distinct_orgs(make_course):
    make_course("course-v1:edX+A+1", org="edX")
    make_course("course-v1:edX+B+1", org="edX")
    make_course("course-v1:MITx+C+1", org="MITx")
    assert services.distinct_orgs() == ["MITx", "edX"]
