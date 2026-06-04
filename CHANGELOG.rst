==========
Change Log
==========

This project adheres to `Semantic Versioning <https://semver.org/>`__
and `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`__.

Unreleased
==========

Added
-----

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

0.1.0 — initial scaffold
========================

* Inventory list, faceted filtering, search, sortable columns.
* Inline tag editing via HTMX partial swaps.
* Saved views (private + shared).
* CSV/TSV streaming export.
* Plugin self-registers via ``cms.djangoapp`` entry point.
