# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parse the inventory querystring into a filter dict and apply it to a
queryset. Kept as pure functions so the export view can reuse the same
pipeline as the listing view.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Q, QuerySet
from django.http import QueryDict
from django.utils import timezone

from .models import CourseTag

ENROLLMENT_BUCKETS = {
    "0": (0, 0),
    "1-10": (1, 10),
    "11-99": (11, 99),
    "100+": (100, None),
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
#
# For ``"str"`` fields we accept any non-empty string up to
# ``_MAX_VALUE_LEN`` unless an enum is supplied. ``"enum"`` is the
# tighter form — the value must be one of the listed strings.
_SCHEMA: dict[str, object] = {
    "q": "str",
    "org": "list",
    "pacing": ("enum_list", {"self", "instructor"}),
    "visibility": "list",
    "last_modified": ("enum", set(LAST_MODIFIED_DAYS) | {"", "older"}),
    "has_owner": ("enum", {"", "yes", "no"}),
    "enrollment": ("enum_list", set(ENROLLMENT_BUCKETS)),
    "tag": "list",
    "sort": ("enum", set(SORTABLE) | {""}),
    "dir": ("enum", {"", "asc", "desc"}),
}


def sanitize_filters(raw: Any) -> dict[str, Any] | None:
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
    out: dict[str, Any] = {}
    for key, want in _SCHEMA.items():
        if key not in raw:
            continue
        value = raw[key]
        kind = want if isinstance(want, str) else want[0]
        allowed = None if isinstance(want, str) else want[1]
        if kind == "str":
            if not isinstance(value, str) or len(value) > _MAX_VALUE_LEN:
                return None
            if value:
                out[key] = value
        elif kind == "enum":
            if not isinstance(value, str) or value not in allowed:
                return None
            if value:
                out[key] = value
        elif kind in ("list", "enum_list"):
            if not isinstance(value, list):
                return None
            cleaned = []
            for item in value:
                if not isinstance(item, str) or len(item) > _MAX_VALUE_LEN:
                    return None
                # Skip empty strings — they're a no-op filter at best
                # and a smuggling channel at worst.
                if not item:
                    continue
                if kind == "enum_list" and item not in allowed:
                    return None
                cleaned.append(item)
            if cleaned:
                out[key] = cleaned
    return out


def parse(get: QueryDict) -> dict[str, Any]:
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


def apply(qs: QuerySet, filters: dict[str, Any]) -> QuerySet:
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
