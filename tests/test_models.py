import pytest
from django.db import IntegrityError
from opaque_keys.edx.keys import CourseKey

from course_inventory.models import CourseTag, SavedView

pytestmark = pytest.mark.django_db


def test_course_tag_unique_together():
    key = CourseKey.from_string("course-v1:edX+A+1")
    CourseTag.objects.create(course_id=key, key="lifecycle", value="active")
    with pytest.raises(IntegrityError):
        CourseTag.objects.create(course_id=key, key="lifecycle", value="active")


def test_course_tag_same_key_different_value_ok():
    key = CourseKey.from_string("course-v1:edX+A+1")
    CourseTag.objects.create(course_id=key, key="lifecycle", value="active")
    CourseTag.objects.create(course_id=key, key="lifecycle", value="archived")
    assert CourseTag.objects.count() == 2


def test_saved_view_unique_per_owner(staff_user, regular_user):
    SavedView.objects.create(name="orphans", owner=staff_user)
    # Same name, different owner is fine.
    SavedView.objects.create(name="orphans", owner=regular_user)
    # Same name, same owner is not.
    with pytest.raises(IntegrityError):
        SavedView.objects.create(name="orphans", owner=staff_user)
