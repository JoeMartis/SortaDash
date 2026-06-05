==========
Change Log
==========

This project adheres to `Semantic Versioning <https://semver.org/>`__
and `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`__.

Unreleased
==========

Added
-----

* Comprehensive end-user documentation (``docs/user/``): install,
  quickstart, facets-and-search, tagging, saved-views, exports,
  configuration, troubleshooting, FAQ.
* Comprehensive developer documentation (``docs/developer/``):
  architecture, extending recipes, testing, release process.
* Consolidated security doc (``docs/security.rst``).
* ``COURSE_INVENTORY_OWNER_ROLES`` setting so deployments with
  non-standard role names (e.g. ``limited_staff``) can widen the
  owner facet.
* ``COURSE_INVENTORY_MAX_FILTERS_JSON_BYTES`` setting (defaults to
  4 KB) to override the saved-view body cap.
* ``make extract_translations`` / ``make compile_translations`` /
  ``make version-check`` targets.
* ``tests/test_scale.py`` — query-budget tests over a 1,000-course
  fixture. Asserts ``base_queryset()`` stays one SELECT,
  ``_page_decorations`` stays two queries, and the end-to-end
  listing stays under 8 plugin queries regardless of catalog size.
* ``scripts/tutor_smoke.sh`` + ``.github/workflows/tutor-smoke.yml``
  — Tutor end-to-end smoke harness. Builds the openedx image with
  the plugin pip-installed, launches Tutor, seeds a course, and
  drives ``/course-inventory/``. Manually triggered
  (workflow_dispatch); too expensive to gate every PR on.
  Validates seven of eight integration phases against a real CMS
  (image build, plugin loading, migrations, URL routing,
  ``@staff_member_required``, ``CourseOverview`` insert + signal);
  the eighth phase (curl-driven assertions with a pre-authenticated
  session through ``SafeSessionMiddleware``) is out of scope per
  ``docs/developer/testing.rst``.

Changed
-------

* ``sanitize_filters`` now validates enum-typed keys (``sort``,
  ``dir``, ``has_owner``, ``last_modified``, ``pacing``,
  ``enrollment``) against their known value sets. Empty strings
  inside list values are silently dropped rather than persisted as
  no-op filters.
* ``_sanitize_csv_cell`` checks the lstripped form so leading
  whitespace can't bypass the formula-injection defense.
* CSV export also defangs ``catalog_visibility`` (consistency with
  ``display_name`` / ``org``).
* Enrollment bucket ``"11-100"`` renamed to ``"11-99"`` so the
  ``"100+"`` bucket (now ``(100, None)``) inclusively contains
  exactly 100. Old saved views referencing ``"11-100"`` will
  silently produce no matches; reapply the facet.
* Tutor plugin ``__version__`` now imports from
  ``course_inventory.__version__`` so the two cannot drift.
* Mutation INFO logs now include ``ip=`` and ``req=`` (from
  ``X-Request-ID``) for audit aggregation.
* Export links use ``qs_replace format='csv'`` so the URL stays
  well-formed when the current request already has a ``format=``
  param.

Removed
-------

* Unused ``old_modified`` and ``recent_modified`` fixtures from
  ``tests/conftest.py``.
* Deprecated ``default_app_config`` from
  ``course_inventory/__init__.py`` (Django auto-discovers
  ``apps.CourseInventoryConfig``).

Fixed
-----

* CI ``audit`` job now uses ``pip-audit --skip-editable`` without
  ``--strict``; ``--strict`` rejects locally-installed packages that
  aren't on PyPI, which made the job always-red.

0.1.0 — initial scaffold
========================

* Hard cap on streaming export (``COURSE_INVENTORY_EXPORT_MAX_ROWS``)
  with a graceful truncation trailer row.
* ``CourseTag.created_by`` for audit attribution on tag mutations.
* ``filters.sanitize_filters`` schema validator for
  ``SavedView.filters_json``.
* CSV/TSV formula-injection defang on export.
* Collision-resistant ``course_dom_id`` template filter for HTMX
  target ids.
* Full i18n coverage; ``course_inventory/locale/`` placeholder.
* CSP-friendly HTMX delivery via ``django-htmx``'s bundled static asset
  (no CDN).
* GitHub Actions CI: lint, build (sdist + wheel), and ``pip-audit``
  jobs; coverage gate at 85%.
* Tutor plugin (``tutor-contrib-course-inventory``) under
  ``tutor-plugin/``.
* Tests: tag/saved-view CRUD, CSV/TSV export, filter validation,
  pagination edge cases, Tutor hook registration, migration
  reversibility, plugin settings hook. 69 tests, ~94% coverage.

Changed
-------

* Listing view no longer mutates ``CourseOverview`` instances — owner
  and tag decorations are passed through a per-request dict to avoid
  leaking attrs into edx-platform's process-wide ``CourseOverview``
  cache.
* Dropped the redundant ``has_owner`` annotation; callers use
  ``owner_count > 0`` directly (one fewer correlated subquery per
  page).
* Tutor init task uses the in-container ``python manage.py cms`` CLI
  (was incorrectly using the host ``./manage.py cms`` wrapper).
* Saved-view "apply" links use ``build_qs`` so list-valued filters
  (multi-org, multi-tag, etc.) survive the round trip.
* Sort-header links reset the page parameter.
* Inventory list view uses ``_visible_saved_views`` helper with
  ``.distinct()`` (no silent inconsistency with the saved-views
  listing).

Fixed
-----

* ``build_qs`` templatetag accepts ``dict_items``; previously crashed
  the inventory list whenever a user had any saved view.
* ``tag_edit`` validates ``tag_id`` as int and returns 400 on bad
  input; previously raised ``ValueError`` → 500.
* ``views.py`` used ``_`` for both the gettext alias and an unpacked
  tuple, causing ``UnboundLocalError`` on the error path.

Removed
-------

* ``course_inventory/permissions.py`` — dead 3-line indirection;
  ``staff_member_required`` is now imported directly.

Security
--------

* ``SavedView.filters_json`` validated against a whitelist; rejected
  if larger than 4 KB or contains nested/non-string values.
* CSV/TSV export sanitizes formula-injection prefixes.
* All mutating actions on ``CourseTag`` and ``SavedView`` are logged
  at ``INFO`` with the acting username.

Foundations (pre-release scaffolding)
=====================================

* Inventory list, faceted filtering, search, sortable columns.
* Inline tag editing via HTMX partial swaps.
* Saved views (private + shared).
* CSV/TSV streaming export.
* Plugin self-registers via ``cms.djangoapp`` entry point.
