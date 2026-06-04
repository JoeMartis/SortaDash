==================
Facets and search
==================

The left rail holds every filter the dashboard supports. Filters
combine with **AND** semantics across categories and **OR** semantics
within a category. The filter state is fully encoded in the URL, so
any view is shareable by copy/paste.

Search box
==========

* Field: ``q``
* Matches: case-insensitive substring on ``display_name``
* Live: results re-render as you type, with a 250 ms debounce

Org
===

* Field: ``org`` (multi-select)
* Comes from the distinct ``org`` column on ``CourseOverview``

Pacing
======

* Field: ``pacing`` (multi-select)
* Values: ``self``, ``instructor``

Visibility
==========

* Field: ``visibility`` (multi-select)
* Values: ``both``, ``about``, ``none``
* Derived from ``CourseOverview.catalog_visibility``

Last modified
=============

* Field: ``last_modified`` (single-select)
* Buckets:

  * ``7d`` — modified in the last 7 days
  * ``30d`` — modified in the last 30 days
  * ``90d`` — modified in the last 90 days
  * ``older`` — older than 90 days
  * empty — any

Owner
=====

* Field: ``has_owner`` (single-select)
* Values: ``yes`` (has at least one ``instructor`` or ``staff`` role),
  ``no`` (orphan), empty (any)

Enrollment
==========

* Field: ``enrollment`` (multi-select)
* Buckets: ``0``, ``1-10``, ``11-99``, ``100+`` (means ≥100)

Tags
====

* Field: ``tag`` (multi-select)
* Format: ``key=value`` per checkbox
* Multiple tag selections AND together: every selected
  ``(key, value)`` must be present on a course for it to match.
  This lets you say "lifecycle=active AND team=platform".

Sort
====

* Fields: ``sort`` (one of ``display_name``, ``org``, ``start``,
  ``modified``, ``enrollment``), ``dir`` (``asc`` / ``desc``)
* Set by clicking the column headers in the table
* Sorting resets ``page`` to 1

Pagination
==========

* Field: ``page`` (1-indexed)
* Page size set by ``COURSE_INVENTORY_PAGE_SIZE`` (default 50)
* ``page`` is reset whenever a filter or sort changes

Shareable URLs
==============

The full filter state is in the querystring. For example::

    https://studio.example.com/course-inventory/?org=edX&org=MITx&pacing=self&q=biology&sort=enrollment&dir=desc

You can copy/paste this URL into a chat, ticket, or saved view.

If you want a stable named link instead, use :doc:`saved-views`.
