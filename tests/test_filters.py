from datetime import UTC, datetime, timedelta

import pytest
from django.http import QueryDict
from opaque_keys.edx.keys import CourseKey

from course_inventory import filters, services
from course_inventory.models import CourseTag

pytestmark = pytest.mark.django_db


def _qd(s):
    return QueryDict(s)


def _apply(get_str):
    parsed = filters.parse(_qd(get_str))
    return filters.apply(services.base_queryset(), parsed)


def test_parse_defaults():
    parsed = filters.parse(_qd(""))
    assert parsed["q"] == ""
    assert parsed["org"] == []
    assert parsed["sort"] == "display_name"
    assert parsed["dir"] == "asc"


def test_search_q_icontains(make_course):
    make_course("course-v1:edX+A+1", display_name="Intro to Biology")
    make_course("course-v1:edX+B+1", display_name="Algorithms")
    ids = list(_apply("q=biology").values_list("id", flat=True))
    assert ids == [CourseKey.from_string("course-v1:edX+A+1")]


def test_filter_by_org(make_course):
    make_course("course-v1:edX+A+1", org="edX")
    make_course("course-v1:MITx+B+1", org="MITx")
    ids = sorted(str(i) for i in _apply("org=MITx").values_list("id", flat=True))
    assert ids == ["course-v1:MITx+B+1"]


def test_filter_by_pacing(make_course):
    make_course("course-v1:edX+A+1", self_paced=True)
    make_course("course-v1:edX+B+1", self_paced=False)
    ids = sorted(str(i) for i in _apply("pacing=self").values_list("id", flat=True))
    assert ids == ["course-v1:edX+A+1"]


def test_filter_last_modified_buckets(make_course):
    now = datetime.now(tz=UTC)
    make_course("course-v1:edX+recent+1", modified=now - timedelta(days=3))
    make_course("course-v1:edX+older+1", modified=now - timedelta(days=120))
    recent_ids = [str(i) for i in _apply("last_modified=7d").values_list("id", flat=True)]
    older_ids = [str(i) for i in _apply("last_modified=older").values_list("id", flat=True)]
    assert recent_ids == ["course-v1:edX+recent+1"]
    assert older_ids == ["course-v1:edX+older+1"]


def test_filter_has_owner(make_course, add_role, staff_user):
    make_course("course-v1:edX+orphan+1")
    owned = make_course("course-v1:edX+owned+1")
    add_role(owned, staff_user, role="instructor")
    yes = [str(i) for i in _apply("has_owner=yes").values_list("id", flat=True)]
    no = [str(i) for i in _apply("has_owner=no").values_list("id", flat=True)]
    assert yes == ["course-v1:edX+owned+1"]
    assert no == ["course-v1:edX+orphan+1"]


def test_filter_enrollment_buckets(make_course, enroll, staff_user, regular_user):
    make_course("course-v1:edX+empty+1")
    one = make_course("course-v1:edX+one+1")
    enroll(one, staff_user)
    small = make_course("course-v1:edX+small+1")
    for u in [staff_user, regular_user]:
        enroll(small, u)

    ids_0 = sorted(str(i) for i in _apply("enrollment=0").values_list("id", flat=True))
    ids_small = sorted(str(i) for i in _apply("enrollment=1-10").values_list("id", flat=True))
    assert ids_0 == ["course-v1:edX+empty+1"]
    assert ids_small == ["course-v1:edX+one+1", "course-v1:edX+small+1"]


def test_filter_by_tag(make_course):
    a = make_course("course-v1:edX+A+1")
    make_course("course-v1:edX+B+1")
    CourseTag.objects.create(course_id=a.id, key="lifecycle", value="active")
    ids = [str(i) for i in _apply("tag=lifecycle%3Dactive").values_list("id", flat=True)]
    assert ids == ["course-v1:edX+A+1"]


def test_sanitize_filters_drops_unknown_keys():
    out = filters.sanitize_filters({"q": "bio", "evil": "x"})
    assert out == {"q": "bio"}


def test_sanitize_filters_accepts_known_lists():
    out = filters.sanitize_filters({"org": ["edX", "MITx"], "tag": ["lifecycle=active"]})
    assert out == {"org": ["edX", "MITx"], "tag": ["lifecycle=active"]}


def test_sanitize_filters_rejects_non_dict():
    assert filters.sanitize_filters([1, 2, 3]) is None
    assert filters.sanitize_filters("nope") is None


def test_sanitize_filters_rejects_nested_objects():
    assert filters.sanitize_filters({"q": {"nested": "x"}}) is None
    assert filters.sanitize_filters({"org": [{"nested": "x"}]}) is None


def test_sanitize_filters_rejects_overlong_values():
    assert filters.sanitize_filters({"q": "x" * 1000}) is None
    assert filters.sanitize_filters({"org": ["x" * 1000]}) is None


def test_sanitize_filters_drops_empty_strings_in_lists():
    """Defense-in-depth: empty entries are a no-op smuggling channel."""
    out = filters.sanitize_filters({"org": ["edX", "", "MITx"]})
    assert out == {"org": ["edX", "MITx"]}


def test_sanitize_filters_validates_sort_enum():
    assert filters.sanitize_filters({"sort": "display_name"}) == {"sort": "display_name"}
    assert filters.sanitize_filters({"sort": "<script>"}) is None
    assert filters.sanitize_filters({"sort": "rogue_column"}) is None


def test_sanitize_filters_validates_dir_enum():
    assert filters.sanitize_filters({"dir": "asc"}) == {"dir": "asc"}
    assert filters.sanitize_filters({"dir": "asc; DROP TABLE"}) is None


def test_sanitize_filters_validates_has_owner_enum():
    assert filters.sanitize_filters({"has_owner": "yes"}) == {"has_owner": "yes"}
    assert filters.sanitize_filters({"has_owner": "maybe"}) is None


def test_sanitize_filters_validates_pacing_enum_list():
    assert filters.sanitize_filters({"pacing": ["self"]}) == {"pacing": ["self"]}
    assert filters.sanitize_filters({"pacing": ["bogus"]}) is None


def test_sanitize_filters_validates_enrollment_enum_list():
    assert filters.sanitize_filters({"enrollment": ["0", "100+"]}) == {"enrollment": ["0", "100+"]}
    assert filters.sanitize_filters({"enrollment": ["bogus"]}) is None


def test_sanitize_filters_validates_last_modified_enum():
    assert filters.sanitize_filters({"last_modified": "7d"}) == {"last_modified": "7d"}
    assert filters.sanitize_filters({"last_modified": "older"}) == {"last_modified": "older"}
    assert filters.sanitize_filters({"last_modified": "yesterday"}) is None


def test_sort_by_modified_desc(make_course):
    older = make_course(
        "course-v1:edX+older+1",
        modified=datetime(2020, 1, 1, tzinfo=UTC),
    )
    newer = make_course(
        "course-v1:edX+newer+1",
        modified=datetime(2026, 1, 1, tzinfo=UTC),
    )
    ids = [str(i) for i in _apply("sort=modified&dir=desc").values_list("id", flat=True)]
    assert ids == [str(newer.id), str(older.id)]
