===========
Saved views
===========

A *saved view* is a name on top of a filter combination. You assemble
a filter by clicking facets on the dashboard, click **Save view**,
give it a name, and (optionally) check **Shared with other staff** so
the rest of the team can see it.

Saved views are stored in the ``course_inventory_savedview`` table.
They contain only the filter dict — not the result set — so they
always reflect current data.

Visibility
==========

* **Private**: visible only to the owner.
* **Shared**: visible to every staff user. Anyone can apply it; only
  the owner can delete it.

The plugin enforces this with ``staff_member_required`` plus an
ownership check on delete (``get_object_or_404(SavedView, pk=pk,
owner=request.user)``).

Where saved views show up
=========================

* In the **Saved views** section of the left facet rail on the
  inventory page (limited list).
* On the dedicated ``/course-inventory/views/`` page (full list with
  owner, shared flag, last-updated, and delete control).

Both apply the view by linking to ``/course-inventory/?…`` with the
stored filter dict serialized into the querystring.

What's stored, and what isn't
=============================

The ``filters_json`` column stores **only** filter keys recognized by
``course_inventory.filters.sanitize_filters``: ``q``, ``org``,
``pacing``, ``visibility``, ``last_modified``, ``has_owner``,
``enrollment``, ``tag``, ``sort``, ``dir``. Unknown keys are dropped
on save.

* Maximum total JSON size: **4 KB** (``MAX_FILTERS_JSON_BYTES``).
* Maximum length of any single value: **256 chars**.
* Lists must contain only strings.

Any input that fails validation is rejected with HTTP 400; the saved
view is not created.

Limits
======

* Saved view names are unique per ``(owner, name)``. You can have two
  saved views called ``Orphans`` if you own one and someone else owns
  the other.
* There is no rename UI in v1. Delete and re-create with the new
  name.

Hand-editing in Django admin
============================

``SavedView`` is registered in Django admin (``/admin/`` →
``course_inventory``). Use admin only for emergency cleanup; the
saved-view UI is the supported path.
