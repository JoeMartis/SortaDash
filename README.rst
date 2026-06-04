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
- CSV/TSV export of the current filtered view (capped, formula-injection
  safe).
- Saved, named views built on tag + facet combinations, optionally
  shared across staff.

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

The Tutor plugin source lives in ``tutor-plugin/`` in this repo. The
plugin self-registers via the ``cms.djangoapp`` entry point, so no
edits to ``edx-platform`` are required.

After install, run migrations and visit::

    https://studio.<your-domain>/course-inventory/

as a staff user.

Configuration
=============

All settings are optional. Defaults are applied by the plugin's
``plugin_settings`` hook; override in ``cms/envs/private.py`` (or your
Tutor patch) to customize.

================================================  =========  ==========================================
Setting                                            Default    Purpose
================================================  =========  ==========================================
``COURSE_INVENTORY_PAGE_SIZE``                     ``50``     Rows per page in the listing view.
``COURSE_INVENTORY_EXPORT_CHUNK_SIZE``             ``500``    DB iterator chunk size for CSV/TSV export.
``COURSE_INVENTORY_EXPORT_MAX_ROWS``               ``10000``  Hard cap on export rows. Above this, the
                                                              stream ends with a ``__TRUNCATED__``
                                                              marker row.
``COURSE_INVENTORY_TAG_KEYS``                      ``["lifecycle", "team", "program", "term"]``
                                                              Suggestion list shown in the inline-tag
                                                              datalist. Operators can add any keys at
                                                              runtime; this only controls the autosuggest.
================================================  =========  ==========================================

Data the plugin reads
=====================

The plugin reads from existing ``edx-platform`` MySQL tables. It does
**not** touch the modulestore (split-mongo) on any code path.

- ``CourseOverview`` (``openedx.core.djangoapps.content.course_overviews``)
  — the spine of the listing: display name, org, start/end, pacing,
  visibility, last-modified.
- ``CourseEnrollment`` (``common.djangoapps.student``) — aggregated as
  a ``COUNT`` per course, never as joined rows.
- ``CourseAccessRole`` (``common.djangoapps.student``) — aggregated as
  a ``COUNT`` per course, and listed per page to surface owners.

The only tables the plugin *writes* are its own:

- ``course_inventory_coursetag`` — operator-defined tags.
- ``course_inventory_savedview`` — named filter combinations.

Migrations to apply
===================

- ``0001_initial`` — creates ``CourseTag`` and ``SavedView``.
- ``0002_coursetag_created_by`` — adds nullable ``created_by`` FK for
  audit attribution on tag mutations.
- ``0003_alter_*`` — metadata only (``verbose_name`` additions for
  i18n); no schema change.

All migrations are reversible.

Security model
==============

- Every URL is gated by ``django.contrib.admin.views.decorators.staff_member_required``.
  Anonymous and non-staff users are redirected to the admin login.
- All state-changing endpoints are CSRF-protected through Django's
  standard middleware; HTMX requests include the session cookie and
  the templates embed ``{% csrf_token %}``.
- The plugin's only writes are to its own two tables. It does not
  modify course content, enrollments, or roles.
- ``SavedView.filters_json`` is validated against a strict schema
  (``filters.sanitize_filters``) before persistence and capped at 4 KB.
  Unknown keys are dropped; nested or oversized values are rejected.
- The CSV/TSV export sanitizes cells beginning with ``=+-@\t\r`` to
  defang Excel/Sheets formula injection from a malicious
  ``display_name``.
- ``CourseTag`` is deliberately a *shared* organizing layer. Any staff
  user can add or remove any tag; ``created_by`` is recorded for audit
  only. Mutating actions are logged at ``INFO`` to
  ``course_inventory.views``.

i18n
====

All user-visible strings are wrapped in ``gettext`` / ``{% trans %}``.
Translations live under ``course_inventory/locale/``. Run::

    cd course_inventory
    django-admin makemessages -l <locale>

to seed a new locale.

Contributing
============

Local dev::

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    pre-commit install
    pytest

CI runs ``pytest`` on Python 3.11 / 3.12 across Django 4.2 / 5.2, plus
``ruff check`` and ``ruff format --check``.

License
=======

AGPL-3.0-or-later, matching the Open edX platform.
