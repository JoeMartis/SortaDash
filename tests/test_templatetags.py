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


def test_qs_toggle_adds_then_removes():
    on = _render("{% qs_toggle 'org' 'MITx' %}", request_get="org=edX")
    assert sorted(parse_qs(on)["org"]) == ["MITx", "edX"]

    off = _render("{% qs_toggle 'org' 'edX' %}", request_get="org=edX&org=MITx")
    assert parse_qs(off)["org"] == ["MITx"]
