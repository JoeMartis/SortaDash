==========
Quickstart
==========

This is the five-minute tour of the dashboard.

Who can use it
==============

Anyone with ``is_staff=True`` on their CMS user account. Non-staff
users are redirected to the admin login.

What you see
============

Visit ``/course-inventory/`` in Studio (e.g.
``https://studio.example.com/course-inventory/``). You'll get one
table with every course on the install:

* ``Display name`` — clickable to sort.
* ``Org`` — the course's organization key.
* ``Start`` / ``End`` — scheduled dates if set.
* ``Pacing`` — ``self`` or ``instructor``.
* ``Visibility`` — derived from ``catalog_visibility``.
* ``Last modified`` — when the course was last edited.
* ``Enrollment`` — count of active enrollments.
* ``Owners`` — usernames with ``instructor`` or ``staff`` access. If
  none, the row reads "orphan" in red.
* ``Tags`` — operator-defined ``key=value`` chips you can add and
  remove inline.

A search bar at the top filters by display name. A left rail provides
faceted filters by org, pacing, visibility, last-modified bucket,
owner presence, enrollment bucket, tag value, and saved view.

Walking through a real workflow
================================

**Goal:** find every "marketing" course that has zero enrollment, tag
them so the team can audit, and save the resulting view for next
quarter.

1. In the search bar, type ``marketing``. Results narrow as you type.
2. In the left rail under **Enrollment**, check the ``0`` bucket.
3. Each remaining row's **Tags** column has a small ``key`` /
   ``value`` form. For each row, type ``audit`` / ``2026q2`` and click
   ``+``. The chip appears immediately.
4. Click **Save view** in the searchbar. Give it a name like
   ``Marketing — zero enrollment, 2026Q2``. Check **Shared with other
   staff** if you want the rest of the team to see it.
5. Visit **Saved views** in the top navigation; the new view appears.
   The link reapplies the same filter combination.

What's deliberately not there
==============================

The dashboard is read-and-organize only. It will not:

* Delete or archive courses.
* Rerun courses.
* Bulk-publish.
* Modify course content of any kind.

The only writes are to the plugin's two tables
(``course_inventory_coursetag`` and ``course_inventory_savedview``).
See :doc:`/security` for the full data model.

Keep going
==========

* :doc:`facets-and-search` for the full filter reference.
* :doc:`tagging` for tag conventions.
* :doc:`saved-views` for sharing views.
* :doc:`exports` for CSV/TSV.
