"""
Parse the inventory querystring into a filter dict and apply it to a
queryset. Kept as pure functions so the export view can reuse the same
pipeline as the listing view.
"""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import CourseTag

ENROLLMENT_BUCKETS = {
    "0": (0, 0),
    "1-10": (1, 10),
    "11-100": (11, 100),
    "100+": (101, None),
}

LAST_MODIFIED_DAYS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
}

SORTABLE = {
    "display_name": "display_name",
    "org": "org",
    "start": "start",
    "modified": "modified",
    "enrollment": "enrollment_count",
}


# Maximum chars accepted for a single filter value, post-validation.
# Wide enough for any legitimate org / tag / search string; narrow
# enough that a stored saved view can't smuggle large payloads through.
_MAX_VALUE_LEN = 256

# Filter shape used by both `parse()` and `sanitize_filters()`. Keys
# absent from this map are dropped on validation; this is the schema
# that lets us safely round-trip saved-view filter blobs.
_SCHEMA = {
    "q": "str",
    "org": "list",
    "pacing": "list",
    "visibility": "list",
    "last_modified": "str",
    "has_owner": "str",
    "enrollment": "list",
    "tag": "list",
    "sort": "str",
    "dir": "str",
}


def sanitize_filters(raw):
    """
    Validate an untrusted filter dict (e.g. the JSON body posted from
    a "save view" form) against the known filter schema.

    Returns a normalized dict on success or ``None`` if the input is
    structurally invalid (not a dict, contains nested objects, has
    overlong values, etc.). Unknown keys are silently dropped. The
    return value is safe to store as ``SavedView.filters_json`` and
    render back through ``build_qs``.
    """
    if not isinstance(raw, dict):
        return None
    out = {}
    for key, want in _SCHEMA.items():
        if key not in raw:
            continue
        value = raw[key]
        if want == "str":
            if not isinstance(value, str) or len(value) > _MAX_VALUE_LEN:
                return None
            if value:
                out[key] = value
        else:  # "list"
            if not isinstance(value, list):
                return None
            cleaned = []
            for item in value:
                if not isinstance(item, str) or len(item) > _MAX_VALUE_LEN:
                    return None
                cleaned.append(item)
            if cleaned:
                out[key] = cleaned
    return out


def parse(get):
    """Convert request.GET into a normalized filter dict."""
    return {
        "q": (get.get("q") or "").strip(),
        "org": get.getlist("org"),
        "pacing": get.getlist("pacing"),
        "visibility": get.getlist("visibility"),
        "last_modified": get.get("last_modified") or "",
        "has_owner": get.get("has_owner") or "",
        "enrollment": get.getlist("enrollment"),
        "tag": get.getlist("tag"),  # entries shaped "key=value"
        "sort": get.get("sort") or "display_name",
        "dir": get.get("dir") or "asc",
    }


def apply(qs, filters):
    if filters["q"]:
        qs = qs.filter(display_name__icontains=filters["q"])

    if filters["org"]:
        qs = qs.filter(org__in=filters["org"])

    if filters["pacing"]:
        self_paced = []
        if "self" in filters["pacing"]:
            self_paced.append(True)
        if "instructor" in filters["pacing"]:
            self_paced.append(False)
        if self_paced:
            qs = qs.filter(self_paced__in=self_paced)

    if filters["visibility"]:
        qs = qs.filter(catalog_visibility__in=filters["visibility"])

    if filters["last_modified"] in LAST_MODIFIED_DAYS:
        cutoff = timezone.now() - timedelta(days=LAST_MODIFIED_DAYS[filters["last_modified"]])
        qs = qs.filter(modified__gte=cutoff)
    elif filters["last_modified"] == "older":
        cutoff = timezone.now() - timedelta(days=90)
        qs = qs.filter(modified__lt=cutoff)

    if filters["has_owner"] == "yes":
        qs = qs.filter(owner_count__gt=0)
    elif filters["has_owner"] == "no":
        qs = qs.filter(owner_count=0)

    if filters["enrollment"]:
        bucket_q = Q()
        for bucket in filters["enrollment"]:
            if bucket not in ENROLLMENT_BUCKETS:
                continue
            lo, hi = ENROLLMENT_BUCKETS[bucket]
            cond = Q(enrollment_count__gte=lo)
            if hi is not None:
                cond &= Q(enrollment_count__lte=hi)
            bucket_q |= cond
        if bucket_q:
            qs = qs.filter(bucket_q)

    for entry in filters["tag"]:
        if "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        qs = qs.filter(id__in=CourseTag.objects.filter(key=key, value=value).values("course_id"))

    sort_field = SORTABLE.get(filters["sort"], "display_name")
    if filters["dir"] == "desc":
        sort_field = f"-{sort_field}"
    qs = qs.order_by(sort_field, "id")

    return qs
