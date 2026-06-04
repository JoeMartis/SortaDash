================
course-inventory
================

A staff-gated administrative dashboard for Open edX Studio (CMS) that
provides a fast, filterable inventory of every course on the install,
plus a lightweight tagging system for organizing them.

It is installed as a standard Open edX Django plugin app and reads
almost entirely from MySQL (``CourseOverview`` + a small handful of
related tables), so it scales cleanly to catalogs of hundreds of
courses without touching the modulestore.

Features (v1)
=============

- Sortable, filterable table of all courses: id, display name, org,
  start/end, pacing, visibility, last modified, enrollment count,
  owners.
- Faceted filtering and display-name search.
- Operator-defined tagging (key/value) orthogonal to org.
- CSV/TSV export of the current filtered view.
- Saved, named views built on tag + facet combinations.

The plugin is deliberately read-and-organize only. No destructive
operations (delete, rerun, bulk-publish) are exposed in v1.

Installation
============

Native pip install into the CMS venv::

    pip install course-inventory

Tutor (quick: pip-only)::

    tutor config save \
      --append OPENEDX_EXTRA_PIP_REQUIREMENTS=course-inventory
    tutor images build openedx
    tutor local launch

Tutor (proper plugin, with auto migrations)::

    pip install tutor-contrib-course-inventory
    tutor plugins enable course-inventory
    tutor config save
    tutor images build openedx
    tutor local launch

The Tutor plugin source lives in ``tutor-plugin/`` in this repo.

The plugin self-registers via the ``cms.djangoapp`` entry point, so no
edits to ``edx-platform`` are required.

Then run migrations and visit::

    https://studio.<your-domain>/course-inventory/

as a staff user.

Configuration
=============

No required settings. Optional knobs live in
``course_inventory/settings/common.py`` (page size, enabled facets).

License
=======

AGPL-3.0-or-later, matching the Open edX platform.
