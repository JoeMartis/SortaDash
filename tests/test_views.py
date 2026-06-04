import json

import pytest
from django.urls import reverse

from course_inventory.models import CourseTag, SavedView

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
    sv = SavedView.objects.get(owner=staff_user, name="orphans")
    assert sv.filters_json == {"has_owner": "no"}


# --- Regression tests for the round-1 review findings ---


def test_inventory_list_renders_when_user_has_saved_view(client, staff_user, make_course):
    """Regression for C1: build_qs used to crash on dict_items."""
    make_course("course-v1:edX+A+1", display_name="A")
    SavedView.objects.create(
        owner=staff_user,
        name="multi",
        filters_json={"org": ["edX", "MITx"], "q": "bio"},
    )
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:inventory"))
    assert response.status_code == 200
    # Multi-value filters survive into the link as repeated params.
    assert b"org=edX" in response.content
    assert b"org=MITx" in response.content


def test_tag_edit_rejects_nonnumeric_tag_id(client, staff_user, make_course):
    """Regression for C2: non-numeric tag_id used to 500."""
    course = make_course("course-v1:edX+A+1")
    client.force_login(staff_user)
    url = reverse("course_inventory:tag_edit", args=[str(course.id)])
    response = client.post(url, {"action": "remove", "tag_id": "not-a-number"})
    assert response.status_code == 400


def test_saved_view_apply_link_handles_list_values(client, staff_user, make_course):
    """Regression for H1: list-valued filters used to render as Python repr."""
    SavedView.objects.create(
        owner=staff_user,
        name="multi",
        filters_json={"org": ["edX", "MITx"]},
    )
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:saved_view_list"))
    assert response.status_code == 200
    assert b"org=edX" in response.content
    assert b"org=MITx" in response.content
    # The broken behavior would render `org=['edX', 'MITx']`.
    assert b"%5B" not in response.content  # url-encoded '['


def test_sort_links_drop_page_param(client, staff_user, make_course):
    """Regression for H2: re-sorting should land you on page 1."""
    make_course("course-v1:edX+A+1", display_name="A")
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:inventory") + "?page=3")
    assert response.status_code == 200
    # The sort header URLs do not preserve `page=3`.
    assert b"sort=display_name" in response.content
    # Every sort link must reset page; the substring `sort=org&amp;dir=asc&amp;page=3` must not appear.
    assert b"page=3" not in response.content.split(b"</nav>")[0]


def test_tag_edit_records_created_by(client, staff_user, make_course):
    """S1: tags are shared but record who added them for audit."""
    course = make_course("course-v1:edX+A+1")
    client.force_login(staff_user)
    url = reverse("course_inventory:tag_edit", args=[str(course.id)])
    client.post(url, {"action": "add", "key": "lifecycle", "value": "active"})
    tag = CourseTag.objects.get(course_id=course.id)
    assert tag.created_by == staff_user


def test_saved_view_create_rejects_oversized_filters_json(client, staff_user):
    """S2: cap on filters_json size."""
    client.force_login(staff_user)
    huge = json.dumps({"q": "x" * 5000})
    response = client.post(
        reverse("course_inventory:saved_view_create"),
        {"name": "huge", "filters_json": huge},
    )
    assert response.status_code == 400
    assert not SavedView.objects.filter(name="huge").exists()


def test_saved_view_create_rejects_invalid_json(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("course_inventory:saved_view_create"),
        {"name": "bad", "filters_json": "not json at all"},
    )
    assert response.status_code == 400
    assert not SavedView.objects.filter(name="bad").exists()


def test_saved_view_create_drops_unknown_keys(client, staff_user):
    """S2: keys outside the schema are silently dropped on save."""
    client.force_login(staff_user)
    response = client.post(
        reverse("course_inventory:saved_view_create"),
        {
            "name": "clean",
            "filters_json": json.dumps({"q": "bio", "evil": "<script>alert(1)</script>"}),
        },
    )
    assert response.status_code == 302
    sv = SavedView.objects.get(owner=staff_user, name="clean")
    assert sv.filters_json == {"q": "bio"}


def test_saved_view_create_rejects_nested_structures(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("course_inventory:saved_view_create"),
        {
            "name": "nested",
            "filters_json": json.dumps({"q": {"nested": "bad"}}),
        },
    )
    assert response.status_code == 400


def test_export_sanitizes_csv_formula_injection(client, staff_user, make_course):
    """S3: display_name beginning with formula prefix gets defanged."""
    make_course(
        "course-v1:edX+A+1",
        display_name='=HYPERLINK("http://evil","click")',
    )
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:export") + "?format=csv")
    body = b"".join(response.streaming_content).decode()
    # The cell must start with a single quote to neuter the formula.
    assert ",'=HYPERLINK" in body or "\"'=HYPERLINK" in body
    assert ",=HYPERLINK" not in body


def test_export_tsv_format(client, staff_user, make_course):
    """TSV branch was previously untested."""
    make_course("course-v1:edX+A+1", display_name="A", org="edX")
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:export") + "?format=tsv")
    body = b"".join(response.streaming_content).decode()
    assert response["Content-Type"].startswith("text/tsv")
    assert "course-inventory.tsv" in response["Content-Disposition"]
    assert "\tedX\t" in body


def test_saved_view_list_shows_own_and_shared(client, staff_user, regular_user):
    SavedView.objects.create(owner=staff_user, name="mine")
    SavedView.objects.create(owner=regular_user, name="theirs-shared", shared=True)
    SavedView.objects.create(owner=regular_user, name="theirs-private")
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:saved_view_list"))
    assert response.status_code == 200
    assert b"mine" in response.content
    assert b"theirs-shared" in response.content
    assert b"theirs-private" not in response.content


def test_saved_view_delete_only_own(client, staff_user, regular_user):
    mine = SavedView.objects.create(owner=staff_user, name="mine")
    theirs = SavedView.objects.create(owner=regular_user, name="theirs")
    client.force_login(staff_user)

    response = client.post(reverse("course_inventory:saved_view_delete", args=[mine.pk]))
    assert response.status_code == 302
    assert not SavedView.objects.filter(pk=mine.pk).exists()

    # Can't delete somebody else's view.
    response = client.post(reverse("course_inventory:saved_view_delete", args=[theirs.pk]))
    assert response.status_code == 404
    assert SavedView.objects.filter(pk=theirs.pk).exists()


def test_saved_view_create_get_renders_form(client, staff_user):
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:saved_view_create") + "?q=bio&org=edX")
    assert response.status_code == 200
    assert b"name" in response.content
    assert b"bio" in response.content


def test_tag_edit_idempotent_add(client, staff_user, make_course):
    """Adding the same tag twice leaves exactly one row."""
    course = make_course("course-v1:edX+A+1")
    client.force_login(staff_user)
    url = reverse("course_inventory:tag_edit", args=[str(course.id)])
    for _ in range(2):
        response = client.post(url, {"action": "add", "key": "lifecycle", "value": "active"})
        assert response.status_code == 200
    assert CourseTag.objects.filter(course_id=course.id).count() == 1


def test_tag_edit_returns_tag_cell_partial(client, staff_user, make_course):
    course = make_course("course-v1:edX+A+1")
    client.force_login(staff_user)
    url = reverse("course_inventory:tag_edit", args=[str(course.id)])
    response = client.post(url, {"action": "add", "key": "lifecycle", "value": "active"})
    # The response is the cell partial, not a full page.
    assert b"<html" not in response.content
    assert b"ci-tag-cell" in response.content


def test_inventory_list_renders_with_no_courses(client, staff_user):
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:inventory"))
    assert response.status_code == 200
    assert b"No courses match" in response.content


# --- Round 2 regression tests ---


def test_export_truncates_at_max_rows(client, staff_user, make_course, settings):
    """M1: export caps row count and emits a truncation marker."""
    settings.COURSE_INVENTORY_EXPORT_MAX_ROWS = 2
    for i in range(5):
        make_course(f"course-v1:edX+C{i}+1", display_name=f"C{i}")
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:export"))
    body = b"".join(response.streaming_content).decode()
    # Two data rows + header + truncation marker (4 lines total).
    assert body.count("\n") == 4
    assert "__TRUNCATED__" in body


def test_htmx_asset_served_from_origin(client, staff_user, make_course):
    """M4: page references the local django-htmx asset, not a CDN."""
    make_course("course-v1:edX+A+1", display_name="A")
    client.force_login(staff_user)
    response = client.get(reverse("course_inventory:inventory"))
    assert b"unpkg.com" not in response.content
    assert b"django_htmx/htmx.min.js" in response.content


def test_inventory_list_handles_garbage_page_param(client, staff_user, make_course):
    """Django's get_page() should coerce bad values to page 1."""
    make_course("course-v1:edX+A+1")
    client.force_login(staff_user)
    for bad in ["abc", "-1", "0", "999999"]:
        response = client.get(reverse("course_inventory:inventory") + f"?page={bad}")
        assert response.status_code == 200, f"page={bad} should not 500"
