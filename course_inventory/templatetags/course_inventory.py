from urllib.parse import urlencode

from django import template

register = template.Library()


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
    return urlencode(items, doseq=True)
