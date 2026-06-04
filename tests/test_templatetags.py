from urllib.parse import parse_qs

from django.http import HttpRequest, QueryDict
from django.template import Context, Template


def _render(template_str, request_get="", context=None):
    request = HttpRequest()
    request.GET = QueryDict(request_get)
    ctx = {"request": request}
    if context:
        ctx.update(context)
    return Template(
        "{% load course_inventory %}{% autoescape off %}" + template_str + "{% endautoescape %}"
    ).render(Context(ctx))


def test_qs_replace_adds_new_param():
    out = _render("{% qs_replace sort='org' %}", request_get="q=hello")
    parsed = parse_qs(out)
    assert parsed == {"q": ["hello"], "sort": ["org"]}


def test_qs_replace_removes_when_empty():
    out = _render("{% qs_replace q='' %}", request_get="q=hello&sort=org")
    parsed = parse_qs(out)
    assert "q" not in parsed
    assert parsed == {"sort": ["org"]}


def test_course_dom_id_avoids_slugify_collision():
    """M3: legacy and v1 course ids must not share a DOM id."""
    from course_inventory.templatetags.course_inventory import course_dom_id

    v1 = course_dom_id("course-v1:edX+A+1")
    legacy = course_dom_id("course-v1:edX/A/1")
    # Both are non-empty 12-char hex strings, but distinct.
    assert v1 != legacy
    assert len(v1) == 12
    assert len(legacy) == 12
    # Same input gives same id (stable across requests).
    assert course_dom_id("course-v1:edX+A+1") == v1


def test_build_qs_accepts_dict_and_dict_items():
    """C1 regression: build_qs must handle dict, dict_items, and pairs."""
    from course_inventory.templatetags.course_inventory import build_qs

    d = {"q": "bio", "org": ["edX", "MITx"]}
    out_dict = build_qs(d)
    out_items = build_qs(d.items())
    out_pairs = build_qs([("q", "bio"), ("org", "edX"), ("org", "MITx")])
    # All three produce the same content (order may vary by dict iteration).
    assert "q=bio" in out_dict
    assert "org=edX" in out_dict
    assert "org=MITx" in out_dict
    assert out_items == out_dict
    assert "q=bio" in out_pairs


def test_qs_toggle_adds_then_removes():
    on = _render("{% qs_toggle 'org' 'MITx' %}", request_get="org=edX")
    assert sorted(parse_qs(on)["org"]) == ["MITx", "edX"]

    off = _render("{% qs_toggle 'org' 'edX' %}", request_get="org=edX&org=MITx")
    assert parse_qs(off)["org"] == ["MITx"]
