=======
Tagging
=======

The tagging layer is intentionally lightweight: ``(key, value)`` pairs
applied to a course, defined by your operators at runtime. There is no
fixed taxonomy.

Conventions we suggest
======================

The plugin ships with a starter list of tag *keys* used by the
inline-add autocomplete. The defaults are:

* ``lifecycle`` — e.g. ``active``, ``archived``, ``draft``,
  ``deprecated``
* ``team`` — e.g. ``platform``, ``science``, ``marketing``
* ``program`` — e.g. ``intro-cs``, ``mba``
* ``term`` — e.g. ``2026q2``, ``fall-2026``

You're free to use any keys you want. Override
``COURSE_INVENTORY_TAG_KEYS`` (see :doc:`configuration`) to change
what the autocomplete suggests.

How tags work
=============

Adding
------

In the **Tags** cell of any row, type a key and value into the small
inline form and click ``+``. The chip appears immediately on success.

Tags are uniquely keyed by ``(course_id, key, value)``. Adding the
same tag twice is a no-op — the row remains exactly once.

Removing
--------

Click the small ``x`` on any chip. The chip disappears immediately on
success.

Filtering by tag
----------------

The left rail's **Tags** section lists every distinct ``key=value``
pair currently in use, with its count. Tick boxes to filter. Multiple
selections combine with **AND** — every selected tag must be present
on a course for it to match.

Sharing
=======

Tags are a shared organizing layer. **Any staff user can add or remove
any tag.** This matches the design intent of an admin surface that the
whole staff team owns. Each tag records who added it (the
``CourseTag.created_by`` field) for audit attribution, but
``created_by`` is *not* enforced as a delete-time ownership boundary.

All mutations are logged at ``INFO`` to the ``course_inventory.views``
logger with the acting username::

    course_inventory tag added: course=course-v1:edX+A+1 lifecycle=active by=staff
    course_inventory tag removed: course=course-v1:edX+A+1 pk=42 by=alice

Operators who need a real audit trail should ensure those logs are
aggregated.

Migrating tag conventions
=========================

When you change a tag taxonomy (e.g. moving from
``lifecycle=archived`` to ``status=retired``), there's no built-in
bulk-edit. Two options:

1. Use the Django shell::

       from course_inventory.models import CourseTag
       CourseTag.objects.filter(key="lifecycle", value="archived").update(
           key="status", value="retired"
       )

2. Add the new tag everywhere first (via filtered checkbox selections
   + inline edit), confirm, then remove the old tag.

Both options are operator actions; the plugin doesn't expose a bulk
UI in v1.
