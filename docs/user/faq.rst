===
FAQ
===

Why a separate plugin instead of patching Studio's existing course
listing?
========================================================================

The Studio dashboard wasn't designed for hundreds of courses, and
patches against ``edx-platform`` core require core-committer review.
A standalone plugin ships independently, installs across releases via
the standard entry-point mechanism, and can be iterated on without
blocking the platform. See the design doc in the repository root for
the full rationale.

Why doesn't it support delete/rerun/bulk-publish?
=================================================

Scope decision for v1. The plugin is read-and-organize only. The risk
of mis-scoping a destructive bulk operation against a 400-course
catalog is not worth the convenience. Use Studio's existing
single-course actions for now.

Why is the tagging system bespoke instead of using ``content_tagging``?
=======================================================================

``content_tagging`` / ``openedx-learning`` taxonomies are heavier and
more opinionated than this admin bookkeeping needs. They're a
candidate for v2 if the plugin graduates into core. The current
``CourseTag`` model is a small dependency-free table the plugin fully
owns.

Why don't tags have per-user ownership?
=======================================

Tags are a shared organizing layer — the design intent is the whole
staff team owning the catalog's taxonomy together. ``created_by`` is
recorded for audit attribution, but it isn't enforced as a delete-time
ownership boundary. See :doc:`tagging` for the full policy.

Can non-staff users see the inventory?
======================================

No. Every view is gated by ``staff_member_required``. Non-staff users
are redirected to the admin login.

Why is there a 4 KB cap on saved-view filter JSON?
===================================================

Saved views can be shared across staff, so an unbounded
``filters_json`` blob is a memory amplification channel — every staff
user's dashboard load would pull the blob into memory. 4 KB is wider
than any legitimate filter dict needs. The cap is hard-coded in
``views.MAX_FILTERS_JSON_BYTES``.

Does the plugin write to course data?
=====================================

No. Its only writes are to its own two tables
(``course_inventory_coursetag``, ``course_inventory_savedview``).

Will the plugin work on Open edX Olive/Palm/Quince?
====================================================

Tested on Sumac, Teak, and ``master``. Earlier releases need at
minimum Django 4.2 and the standard ``cms.djangoapp`` plugin loader.
PRs welcome to widen the support window.

Is there an MFE version?
========================

Not in v1. Server-rendered Django + HTMX was the fastest path. If
the plugin graduates into core, building it as a first-class Studio
MFE is the natural next step.

Can I run two instances in different orgs?
==========================================

The plugin is a single Django app, so there's one install per CMS
process. Filtering by ``org`` (which is multi-select) is the way to
get per-org views. Multi-tenant in the sense of separate auth
boundaries isn't supported.

How do I generate translations?
================================

The plugin uses Django's ``gettext`` machinery throughout. From
``course_inventory/`` run::

    django-admin makemessages -l <locale>

A ``locale/`` directory ships in the repo with a placeholder. PRs
with new translations are very welcome.
