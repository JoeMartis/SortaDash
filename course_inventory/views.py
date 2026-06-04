# SPDX-License-Identifier: AGPL-3.0-or-later
import csv
import json
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from . import filters, services
from .forms import CourseTagForm, SavedViewForm
from .models import CourseTag, SavedView

log = logging.getLogger(__name__)

# Default cap on JSON body accepted into SavedView.filters_json.
# Real lookups go through the COURSE_INVENTORY_MAX_FILTERS_JSON_BYTES
# setting; this is the fallback when settings aren't loaded.
_DEFAULT_MAX_FILTERS_JSON_BYTES = 4 * 1024

# Characters that Excel/Sheets will treat as the start of a formula
# when a CSV cell begins with them. We prefix with a single quote on
# export to defang.
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _paginate(request: HttpRequest, qs: QuerySet) -> "Paginator":
    page_size = getattr(settings, "COURSE_INVENTORY_PAGE_SIZE", 50)
    paginator = Paginator(qs, page_size)
    return paginator.get_page(request.GET.get("page") or 1)


def _page_decorations(page) -> dict:
    """
    Build per-row owners and tags for the page.

    Returns ``{course_id: {"owners": [usernames], "tags": [CourseTag]}}``
    for the templates to look up. Two queries total, regardless of page
    size.

    Importantly we do *not* mutate the ``CourseOverview`` instances
    themselves — those are cached process-wide in edx-platform, so
    attaching per-request attributes to them would leak across
    requests.
    """
    course_ids = [c.id for c in page.object_list]
    owners = services.owners_for(course_ids)
    tags = services.tags_for(course_ids)
    return {cid: {"owners": owners.get(cid, []), "tags": tags.get(cid, [])} for cid in course_ids}


def _visible_saved_views(user) -> QuerySet[SavedView]:
    """The user's own saved views plus any shared views."""
    return (SavedView.objects.filter(owner=user) | SavedView.objects.filter(shared=True)).distinct()


def _sanitize_csv_cell(value):
    """
    Defang Excel/Sheets formula injection in a CSV cell.

    Sheets and many CSV importers strip leading whitespace before
    evaluating the first character, so we must check the lstripped
    form — ``" =SUM(A1)"`` is just as dangerous as ``"=SUM(A1)"``.
    """
    if isinstance(value, str) and value.lstrip().startswith(_CSV_INJECTION_PREFIXES):
        return "'" + value
    return value


@staff_member_required
def inventory_list(request: HttpRequest) -> HttpResponse:
    parsed = filters.parse(request.GET)
    qs = filters.apply(services.base_queryset(), parsed)
    page = _paginate(request, qs)
    decorations = _page_decorations(page)

    context = {
        "page": page,
        "decorations": decorations,
        "filters": parsed,
        "orgs": services.distinct_orgs(),
        "tag_values": services.distinct_tag_values(),
        "tag_keys": getattr(
            settings,
            "COURSE_INVENTORY_TAG_KEYS",
            ["lifecycle", "team", "program", "term"],
        ),
        "querystring": request.GET.urlencode(),
        "saved_views": _visible_saved_views(request.user),
    }
    # HTMX requests get just the table partial so facet/search changes
    # can swap #inventory-table without a full page reload.
    template = (
        "course_inventory/_table.html"
        if request.headers.get("HX-Request")
        else "course_inventory/inventory_list.html"
    )
    return render(request, template, context)


@staff_member_required
def export(request: HttpRequest) -> StreamingHttpResponse:
    fmt = "tsv" if request.GET.get("format") == "tsv" else "csv"
    delim = "\t" if fmt == "tsv" else ","
    parsed = filters.parse(request.GET)
    qs = filters.apply(services.base_queryset(), parsed)

    columns = [
        "course_id",
        "display_name",
        "org",
        "start",
        "end",
        "pacing",
        "visibility",
        "modified",
        "enrollment_count",
        "owner_count",
    ]

    chunk_size = getattr(settings, "COURSE_INVENTORY_EXPORT_CHUNK_SIZE", 500)
    max_rows = getattr(settings, "COURSE_INVENTORY_EXPORT_MAX_ROWS", 10_000)

    # Standard Django streaming-CSV pattern: a pseudo file-like object
    # whose write() returns the rendered line, which the generator then
    # yields. See docs/howto/outputting-csv (streaming responses).
    class Echo:
        def write(self, value):
            return value

    writer = csv.writer(Echo(), delimiter=delim)

    def rows():
        yield writer.writerow(columns)
        emitted = 0
        for c in qs.iterator(chunk_size=chunk_size):
            if emitted >= max_rows:
                # Trailer row makes it explicit to anyone opening the
                # file that the export was truncated. Keeps the file
                # well-formed CSV/TSV — no trailing partial rows.
                yield writer.writerow(
                    [f"__TRUNCATED__ at {max_rows} rows; narrow your filters and re-export"]
                )
                return
            yield writer.writerow(
                [
                    str(c.id),
                    _sanitize_csv_cell(c.display_name or ""),
                    _sanitize_csv_cell(c.org or ""),
                    c.start.isoformat() if c.start else "",
                    c.end.isoformat() if c.end else "",
                    "self" if c.self_paced else "instructor",
                    _sanitize_csv_cell(c.catalog_visibility or ""),
                    c.modified.isoformat() if c.modified else "",
                    c.enrollment_count,
                    c.owner_count,
                ]
            )
            emitted += 1

    response = StreamingHttpResponse(rows(), content_type=f"text/{fmt}")
    response["Content-Disposition"] = f'attachment; filename="course-inventory.{fmt}"'
    return response


@staff_member_required
@require_POST
def tag_edit(request: HttpRequest, course_key: str) -> HttpResponse:
    try:
        key = CourseKey.from_string(course_key)
    except InvalidKeyError:
        return HttpResponseBadRequest(_("invalid course key"))

    action = request.POST.get("action", "add")

    if action == "add":
        form = CourseTagForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest(_("invalid tag"))
        tag, created = CourseTag.objects.get_or_create(
            course_id=key,
            key=form.cleaned_data["key"],
            value=form.cleaned_data["value"],
            defaults={"created_by": request.user},
        )
        if created:
            log.info(
                "course_inventory tag added: course=%s %s=%s by=%s ip=%s req=%s",
                key,
                tag.key,
                tag.value,
                request.user.username,
                request.META.get("REMOTE_ADDR", ""),
                request.headers.get("X-Request-ID", ""),
            )
    elif action == "remove":
        try:
            tag_id = int(request.POST.get("tag_id", ""))
        except (TypeError, ValueError):
            return HttpResponseBadRequest(_("invalid tag_id"))
        deleted, _per_model = CourseTag.objects.filter(pk=tag_id, course_id=key).delete()
        if deleted:
            log.info(
                "course_inventory tag removed: course=%s pk=%s by=%s ip=%s req=%s",
                key,
                tag_id,
                request.user.username,
                request.META.get("REMOTE_ADDR", ""),
                request.headers.get("X-Request-ID", ""),
            )
    else:
        return HttpResponseBadRequest(_("unknown action"))

    # Re-render just this row's tag cell for HTMX swap.
    tags = list(CourseTag.objects.filter(course_id=key))
    return render(
        request,
        "course_inventory/_tag_cell.html",
        {"course_id": key, "tags": tags},
    )


@staff_member_required
def saved_view_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "course_inventory/saved_view_list.html",
        {"views": _visible_saved_views(request.user)},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def saved_view_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SavedViewForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "course_inventory/saved_view_form.html",
                {"form": form, "querystring": "", "filters_json": "{}"},
            )

        raw = request.POST.get("filters_json") or "{}"
        max_bytes = getattr(
            settings,
            "COURSE_INVENTORY_MAX_FILTERS_JSON_BYTES",
            _DEFAULT_MAX_FILTERS_JSON_BYTES,
        )
        if len(raw.encode("utf-8")) > max_bytes:
            return HttpResponseBadRequest(_("filters_json too large"))
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return HttpResponseBadRequest(_("filters_json is not valid JSON"))
        sanitized = filters.sanitize_filters(parsed)
        if sanitized is None:
            return HttpResponseBadRequest(_("filters_json failed validation"))

        obj = form.save(commit=False)
        obj.owner = request.user
        obj.filters_json = sanitized
        obj.save()
        log.info(
            "course_inventory saved_view created: name=%s shared=%s by=%s ip=%s req=%s",
            obj.name,
            obj.shared,
            request.user.username,
            request.META.get("REMOTE_ADDR", ""),
            request.headers.get("X-Request-ID", ""),
        )
        return HttpResponseRedirect(reverse("course_inventory:saved_view_list"))

    return render(
        request,
        "course_inventory/saved_view_form.html",
        {
            "form": SavedViewForm(),
            "querystring": request.GET.urlencode(),
            "filters_json": json.dumps(filters.parse(request.GET)),
        },
    )


@staff_member_required
@require_POST
def saved_view_delete(request: HttpRequest, pk: int) -> HttpResponse:
    view = get_object_or_404(SavedView, pk=pk, owner=request.user)
    view.delete()
    log.info(
        "course_inventory saved_view deleted: pk=%s by=%s ip=%s req=%s",
        pk,
        request.user.username,
        request.META.get("REMOTE_ADDR", ""),
        request.headers.get("X-Request-ID", ""),
    )
    return HttpResponseRedirect(reverse("course_inventory:saved_view_list"))
