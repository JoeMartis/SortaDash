# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
from urllib.parse import urlencode

from django import template

register = template.Library()


@register.filter(name="course_dom_id")
def course_dom_id(course_id):
    """
    Stable, collision-resistant DOM id for a course.

    `slugify()` is not safe here: course ids like ``course-v1:edX+A+1``
    and ``course-v1:edX/A/1`` slugify to the same value, which would
    cause HTMX swaps to target the wrong row. Hash the canonical
    string form instead — short enough to stay readable, wide enough
    that collisions are not a practical concern.
    """
    digest = hashlib.sha1(str(course_id).encode("utf-8"), usedforsecurity=False)
    return digest.hexdigest()[:12]


@register.simple_tag(takes_context=True)
def qs_replace(context, **overrides):
    """
    Return the current request.GET querystring with the given keys
    replaced/removed. Used to build sort and pagination links that
    preserve current filters.
    """
    request = context["request"]
    params = request.GET.copy()
    for key, value in overrides.items():
        if value is None or value == "":
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


@register.simple_tag(takes_context=True)
def qs_toggle(context, key, value):
    """Toggle a multi-value query param (used by facet checkboxes)."""
    request = context["request"]
    params = request.GET.copy()
    existing = params.getlist(key)
    if value in existing:
        existing.remove(value)
    else:
        existing.append(value)
    params.setlist(key, existing)
    return params.urlencode()


@register.filter
def get_item(d, key):
    if hasattr(d, "get"):
        return d.get(key)
    return None


@register.simple_tag
def build_qs(items):
    """
    Render a filter mapping as a URL querystring.

    Accepts a dict, a dict_items view, or any iterable of (key, value)
    pairs. Multi-value entries (lists) are expanded into repeated keys.
    """
    if hasattr(items, "items"):
        pairs = list(items.items())
    else:
        pairs = list(items)
    expanded = []
    for k, v in pairs:
        if isinstance(v, (list, tuple)):
            for item in v:
                if item not in (None, ""):
                    expanded.append((k, item))
        elif v not in (None, ""):
            expanded.append((k, v))
    return urlencode(expanded, doseq=True)
