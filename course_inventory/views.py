import csv
import json

from django.conf import settings
from django.core.paginator import Paginator
from django.http import (
    HttpResponseBadRequest,
    HttpResponseRedirect,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from . import filters, services
from .forms import CourseTagForm, SavedViewForm
from .models import CourseTag, SavedView
from .permissions import staff_member_required


def _paginate(request, qs):
    page_size = getattr(settings, "COURSE_INVENTORY_PAGE_SIZE", 50)
    paginator = Paginator(qs, page_size)
    return paginator.get_page(request.GET.get("page") or 1)


def _decorate_page(page):
    """Attach owners + tags to each row in a page (two queries total)."""
    course_ids = [c.id for c in page.object_list]
    owners = services.owners_for(course_ids)
    tags = services.tags_for(course_ids)
    for course in page.object_list:
        course.owner_usernames = owners.get(course.id, [])
        course.tags = tags.get(course.id, [])
    return page


@staff_member_required
def inventory_list(request):
    parsed = filters.parse(request.GET)
    qs = filters.apply(services.base_queryset(), parsed)
    page = _decorate_page(_paginate(request, qs))

    context = {
        "page": page,
        "filters": parsed,
        "orgs": services.distinct_orgs(),
        "tag_values": services.distinct_tag_values(),
        "tag_keys": getattr(
            settings,
            "COURSE_INVENTORY_TAG_KEYS",
            ["lifecycle", "team", "program", "term"],
        ),
        "querystring": request.GET.urlencode(),
        "saved_views": SavedView.objects.filter(owner=request.user)
        | (SavedView.objects.filter(shared=True)),
    }
    template = (
        "course_inventory/_table.html"
        if request.headers.get("HX-Request")
        else "course_inventory/inventory_list.html"
    )
    return render(request, template, context)


@staff_member_required
def export(request):
    fmt = request.GET.get("format", "csv")
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

    class Echo:
        def write(self, value):
            return value

    writer = csv.writer(Echo(), delimiter=delim)

    def rows():
        yield writer.writerow(columns)
        for c in qs.iterator(chunk_size=chunk_size):
            yield writer.writerow(
                [
                    str(c.id),
                    c.display_name or "",
                    c.org or "",
                    c.start.isoformat() if c.start else "",
                    c.end.isoformat() if c.end else "",
                    "self" if c.self_paced else "instructor",
                    c.catalog_visibility or "",
                    c.modified.isoformat() if c.modified else "",
                    c.enrollment_count,
                    c.owner_count,
                ]
            )

    response = StreamingHttpResponse(
        rows(),
        content_type=f"text/{fmt}",
    )
    response["Content-Disposition"] = f'attachment; filename="course-inventory.{fmt}"'
    return response


@staff_member_required
@require_POST
def tag_edit(request, course_key):
    try:
        key = CourseKey.from_string(course_key)
    except InvalidKeyError:
        return HttpResponseBadRequest("invalid course key")

    action = request.POST.get("action", "add")

    if action == "add":
        form = CourseTagForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest("invalid tag")
        CourseTag.objects.get_or_create(
            course_id=key,
            key=form.cleaned_data["key"],
            value=form.cleaned_data["value"],
        )
    elif action == "remove":
        tag_id = request.POST.get("tag_id")
        CourseTag.objects.filter(pk=tag_id, course_id=key).delete()
    else:
        return HttpResponseBadRequest("unknown action")

    # Re-render just this row's tag cell for HTMX swap.
    tags = list(CourseTag.objects.filter(course_id=key))
    return render(
        request,
        "course_inventory/_tag_cell.html",
        {"course_id": key, "tags": tags},
    )


@staff_member_required
def saved_view_list(request):
    views_qs = SavedView.objects.filter(owner=request.user) | (
        SavedView.objects.filter(shared=True)
    )
    return render(
        request,
        "course_inventory/saved_view_list.html",
        {"views": views_qs.distinct()},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def saved_view_create(request):
    if request.method == "POST":
        form = SavedViewForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            try:
                obj.filters_json = json.loads(request.POST.get("filters_json") or "{}")
            except json.JSONDecodeError:
                obj.filters_json = {}
            obj.save()
            return HttpResponseRedirect(reverse("course_inventory:saved_view_list"))
    else:
        form = SavedViewForm()
    return render(
        request,
        "course_inventory/saved_view_form.html",
        {
            "form": form,
            "querystring": request.GET.urlencode(),
            "filters_json": json.dumps(filters.parse(request.GET)),
        },
    )


@staff_member_required
@require_POST
def saved_view_delete(request, pk):
    view = get_object_or_404(SavedView, pk=pk, owner=request.user)
    view.delete()
    return HttpResponseRedirect(reverse("course_inventory:saved_view_list"))
