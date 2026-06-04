import pytest
from django.urls import reverse

from course_inventory.models import CourseTag

pytestmark = pytest.mark.django_db


def test_inventory_redirects_anonymous(client):
    response = client.get(reverse("course_inventory:inventory"))
    assert response.status_code == 302
    assert "/admin/login" in response.url or "/login" in response.url


def test_inventory_forbidden_for_non_staff(client, regular_user):
    client.force_login(regular_user)
    response = client.get(reverse("course_inventory:inventory"))
    # staff_member_required redirects to the admin login on failure.
    assert response.status_code == 302


def test_inventory_renders_for_staff(client, staff_user, make_course):
    make_course("course-v1:edX+A+1", display_name="Intro to Biology")
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:inventory"))
    assert response.status_code == 200
    assert b"Intro to Biology" in response.content


def test_htmx_request_returns_partial(client, staff_user, make_course):
    make_course("course-v1:edX+A+1", display_name="Intro to Biology")
    client.force_login(staff_user)
    response = client.get(
        reverse("course_inventory:inventory"),
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    # Partial doesn't include the page chrome.
    assert b"<html" not in response.content
    assert b"Intro to Biology" in response.content


def test_export_streams_csv_with_filtered_rows(client, staff_user, make_course):
    make_course("course-v1:edX+A+1", display_name="Match", org="edX")
    make_course("course-v1:MITx+B+1", display_name="Skip", org="MITx")
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:export") + "?org=edX&format=csv")
    body = b"".join(response.streaming_content).decode()
    assert response["Content-Type"].startswith("text/csv")
    assert "Match" in body
    assert "Skip" not in body


def test_tag_edit_add_and_remove(client, staff_user, make_course):
    course = make_course("course-v1:edX+A+1")
    client.force_login(staff_user)
    url = reverse("course_inventory:tag_edit", args=[str(course.id)])
    response = client.post(url, {"action": "add", "key": "lifecycle", "value": "active"})
    assert response.status_code == 200
    assert CourseTag.objects.filter(course_id=course.id).count() == 1

    tag = CourseTag.objects.get(course_id=course.id)
    response = client.post(url, {"action": "remove", "tag_id": tag.pk})
    assert response.status_code == 200
    assert not CourseTag.objects.filter(course_id=course.id).exists()


def test_tag_edit_rejects_invalid_course_key(client, staff_user):
    client.force_login(staff_user)
    url = reverse("course_inventory:tag_edit", args=["not-a-course-key"])
    response = client.post(url, {"action": "add", "key": "lifecycle", "value": "active"})
    assert response.status_code == 400


def test_saved_view_create_persists_filters(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("course_inventory:saved_view_create"),
        {
            "name": "orphans",
            "filters_json": '{"has_owner": "no"}',
        },
    )
    assert response.status_code == 302
    from course_inventory.models import SavedView

    sv = SavedView.objects.get(owner=staff_user, name="orphans")
    assert sv.filters_json == {"has_owner": "no"}
