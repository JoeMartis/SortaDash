========
Security
========

Trust model
===========

The plugin lives inside the CMS process and trusts the host's auth.

* **Anonymous users** — blocked by ``staff_member_required``;
  redirected to the admin login.
* **Authenticated non-staff users** — same redirect; no leakage.
* **Staff users** (``is_staff=True``) — full read access to every
  course's metadata that ``CourseOverview`` exposes, full read/write
  on the plugin's two tables, full export.
* **Course teams** without ``is_staff`` — out of the trust boundary.
  The plugin never modifies course content, so course teams can't
  be affected by anything a staff user does here. But operator-author
  fields like ``display_name`` flow through; see "Course-authored
  content" below.

The plugin does not invent its own permission system. If your install
needs course-creator-group scoping or per-org access, the
``staff_member_required`` import in ``views.py`` is the single
boundary to swap.

Data the plugin reads
=====================

Read-only, from existing MySQL tables:

* ``CourseOverview`` — display name, org, start/end, pacing,
  catalog visibility, last modified.
* ``CourseEnrollment`` — aggregated as a ``COUNT`` per course
  (correlated subquery).
* ``CourseAccessRole`` — aggregated as a ``COUNT``, then re-queried
  per visible page to surface owner usernames.

The plugin never reads:

* The modulestore (split-mongo).
* Course content of any kind.
* User PII beyond ``username``.
* Grade or progress data.

Data the plugin writes
======================

The only two tables the plugin owns:

* ``course_inventory_coursetag`` —
  ``(course_id, key, value, created_at, created_by)``.
* ``course_inventory_savedview`` —
  ``(name, owner, filters_json, shared, created_at, updated_at)``.

All writes happen through the plugin's six view functions. There is
no public API; there are no signals; there are no Celery tasks.

CSRF
====

Every state-changing endpoint is CSRF-protected through Django's
standard middleware. HTMX requests carry the session cookie and the
templates embed ``{% csrf_token %}``. No view uses
``@csrf_exempt``.

Authorization
=============

* All views: ``@staff_member_required``.
* ``saved_view_delete``: additionally scopes via
  ``get_object_or_404(SavedView, pk=pk, owner=request.user)`` — a
  staff user cannot delete another user's view.
* ``CourseTag`` mutations are deliberately *not* per-user scoped
  (shared organizing layer). Audit-attributed via ``created_by`` and
  logged at ``INFO``.

Validation boundaries
=====================

* **``CourseKey.from_string``** — ``tag_edit`` parses the URL-path
  ``course_key`` arg. Invalid keys → 400.
* **``tag_id``** — coerced to ``int``; non-numeric → 400.
* **``CourseTagForm``** — validates ``key`` (≤64 chars) and ``value``
  (≤128 chars) on add.
* **``SavedViewForm``** — ModelForm validation on name + shared
  fields.
* **``filters.sanitize_filters``** — schema validator for
  ``filters_json``:

  * Whitelist of keys: ``q``, ``org``, ``pacing``, ``visibility``,
    ``last_modified``, ``has_owner``, ``enrollment``, ``tag``,
    ``sort``, ``dir``.
  * Strings ≤ 256 chars; lists must contain only strings ≤ 256 chars.
  * Unknown keys silently dropped. Nested / non-string values
    rejected with 400.

* **Raw JSON body cap** — ``MAX_FILTERS_JSON_BYTES`` (4 KB) on the
  POST body before ``json.loads``. Defends against amplification
  through the shared-saved-view channel.

Injection defenses
==================

* **HTML / XSS** — every template uses Django's autoescape; no
  ``|safe`` or ``mark_safe`` anywhere in production templates.
  Operator-author strings (``display_name``, ``org``, tag values)
  appear in text contexts only.
* **SQL** — no raw SQL, no ``.extra()``, no ``RawSQL``. All queries
  go through the ORM.
* **CSV/TSV formula** — ``_sanitize_csv_cell`` prefixes ``'`` to any
  cell starting with ``=``, ``+``, ``-``, ``@``, ``\t``, ``\r``
  (or those chars after leading whitespace). Applied to
  ``display_name``, ``org``, and ``catalog_visibility``.
* **DOM-id collision** — HTMX target ids are derived via
  ``course_dom_id`` (SHA-1, 12 hex chars,
  ``usedforsecurity=False``). ``slugify`` would collide on
  ``course-v1:edX+A+1`` vs ``course-v1:edX/A/1``.
* **Open-redirect / parameter smuggling** — saved-view "apply" links
  are built with ``build_qs``, which URL-encodes via
  ``urlencode(doseq=True)``.

Logging and audit
=================

Mutations on ``CourseTag`` and ``SavedView`` log at ``INFO`` to the
``course_inventory.views`` logger::

    course_inventory tag added: course=course-v1:edX+A+1 lifecycle=active by=alice
    course_inventory tag removed: course=course-v1:edX+A+1 pk=42 by=alice
    course_inventory saved_view created: name=orphans shared=False by=alice
    course_inventory saved_view deleted: pk=7 by=alice

Operators who need a real audit trail should aggregate
``course_inventory.views`` INFO logs.

What the plugin does NOT defend against
========================================

* **Compromised staff account.** Out of scope; the platform's auth
  is the trust boundary.
* **CSP/SOP at the host level.** The plugin loads HTMX from a
  same-origin static file (``django_htmx`` package). It does not set
  CSP headers; those are the host CMS's job.
* **Rate limiting.** No view rate-limits. For an admin tool gated
  by ``is_staff`` this is acceptable in v1.
* **Operator-controlled Tutor config.** A malicious
  ``COURSE_INVENTORY_PIP_SPEC`` could inject into the
  Dockerfile's ``RUN pip install '...'`` shell. Operator trust
  boundary, documented in ``tutor-plugin/tutorcourseinventory/plugin.py``.

Reporting a vulnerability
=========================

Email the maintainers privately; do not open a public GitHub issue.
See the
`Open edX disclosure process <https://openedx.org/security>`__.
