============
Architecture
============

This document is the map for anyone modifying the plugin. For *why*
the plugin exists in the first place, see the design doc in the
repo root.

One-paragraph summary
=====================

A Django plugin app loaded into the CMS process. Reads from existing
``edx-platform`` MySQL tables via lazy imports (no modulestore on
any code path). Writes only to its own two tables. Frontend is
server-rendered Django templates with HTMX for the interactive bits.

Module map
==========

::

    course_inventory/
      apps.py              # CourseInventoryConfig + plugin_app dict
      urls.py              # all routes under /course-inventory/
      models.py            # CourseTag + SavedView
      services.py          # the listing query and the facet helpers
      filters.py           # querystring → filter dict → queryset filter
      forms.py             # tag-add form + saved-view form
      views.py             # the six view functions + helpers
      admin.py             # Django admin registration
      settings/common.py   # plugin_settings hook
      templatetags/
        course_inventory.py   # build_qs, qs_replace, qs_toggle,
                              # course_dom_id, get_item
      templates/course_inventory/
        base.html, inventory_list.html, _table.html, _row.html,
        _facet_panel.html, _tag_cell.html,
        saved_view_form.html, saved_view_list.html
      static/course_inventory/
        css/inventory.css, js/inventory.js
      locale/                # gettext .po files (one per locale)
      migrations/

    tutor-plugin/            # companion Tutor plugin
      tutorcourseinventory/
        plugin.py            # CONFIG_DEFAULTS + ENV_PATCHES + INIT_TASKS

    tests/                   # see developer/testing.rst

Data flow
=========

A request to ``/course-inventory/`` traces as::

    request
      → views.inventory_list
          → filters.parse(request.GET)        # parses querystring
          → services.base_queryset()          # one annotated CourseOverview qs
          → filters.apply(qs, parsed)         # narrows by facet
          → _paginate(request, qs)            # Paginator(get_page)
          → _page_decorations(page)           # owners + tags per row
          → _visible_saved_views(user)        # owner OR shared
          → render("inventory_list.html" or "_table.html" if HX-Request)

The HTMX partial path returns just the table block on filter/search
changes; the full page is only re-rendered on initial load or hard
navigation.

The query model
===============

``services.base_queryset()`` returns a ``CourseOverview`` queryset
annotated with:

* ``enrollment_count`` — count of ``CourseEnrollment`` with
  ``is_active=True``, via correlated subquery.
* ``owner_count`` — count of ``CourseAccessRole`` with role in
  ``("instructor", "staff")``, via correlated subquery.

Neither annotation joins multiple rows per course. The page render
runs exactly:

1. one COUNT for pagination,
2. one SELECT for the page (with the two subqueries inline),
3. one SELECT for owners on the visible course ids,
4. one SELECT for tags on the visible course ids,
5. one SELECT each for the facet panel helpers
   (``distinct_orgs``, ``distinct_tag_values``).

This shape is the reason the dashboard stays fast at 400+ courses.

The lazy-import shim
====================

``services._lazy_imports()`` imports ``CourseOverview``,
``CourseEnrollment``, and ``CourseAccessRole`` at *call* time, not
at module import time. This lets the package be imported in plain
Django environments (e.g. ``makemigrations --check``) where
``edx-platform`` isn't installed.

The test suite leverages this: ``tests/openedx/`` and
``tests/common/`` are namespace-package shims that resolve to
``tests.stubs.models`` — small Django models that stand in for the
real platform models. See :doc:`testing`.

Tag mutation flow
=================

``POST /course-inventory/tag/<course_key>``:

1. ``staff_member_required`` gates.
2. ``CourseKey.from_string`` parses the path arg; invalid → 400.
3. action=add: ``CourseTagForm.is_valid()`` → ``get_or_create`` with
   ``defaults={"created_by": request.user}``; INFO log on create.
4. action=remove: ``int(tag_id)`` validation → ``.filter().delete()``;
   INFO log on success.
5. Returns just the ``_tag_cell.html`` partial for HTMX swap.

Saved-view flow
===============

``GET /course-inventory/views/new?<filters>``: render the form
pre-populated with the JSON-serialized parsed filters.

``POST /course-inventory/views/new``:

1. Read ``filters_json`` from POST body.
2. Reject if larger than ``MAX_FILTERS_JSON_BYTES`` (4 KB).
3. ``json.loads`` → ``filters.sanitize_filters``. Reject on
   structural failure.
4. Persist with ``owner=request.user``.

``POST /course-inventory/views/<pk>/delete`` enforces ownership at
the query level: ``get_object_or_404(SavedView, pk=pk,
owner=request.user)``.

Why HTMX
========

* Faceted filtering needs partial swaps to stay fast and to preserve
  scroll position.
* Inline tag editing wants a sub-row partial without bringing in a
  build toolchain.
* HTMX is delivered by ``django-htmx`` as a same-origin static asset,
  so we never hit a CDN and CSP-strict deployments are fine.

If the plugin ever graduates into a first-class MFE in core, the
backend already speaks JSON-ish (the export pipeline is one
example); the React surface would replace the templates only.

Tutor companion plugin
======================

``tutor-plugin/tutorcourseinventory/plugin.py`` registers three Tutor
hooks:

* ``CONFIG_DEFAULTS`` — adds ``COURSE_INVENTORY_VERSION`` and
  ``COURSE_INVENTORY_PIP_SPEC`` so operators can override the install
  source.
* ``ENV_PATCHES`` — appends ``RUN pip install
  '{{ COURSE_INVENTORY_PIP_SPEC }}'`` to the openedx Dockerfile.
* ``CLI_DO_INIT_TASKS`` — runs ``python manage.py cms migrate
  course_inventory`` during ``tutor … do init``.

Things to read next
===================

* :doc:`extending` — recipes for adding facets / columns / tag keys.
* :doc:`testing` — the stub layer and the test patterns.
* :doc:`/security` — trust model, audit, validation boundaries.
