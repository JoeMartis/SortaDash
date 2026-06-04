===============
Troubleshooting
===============

``/course-inventory/`` returns 404
==================================

Cause: the CMS process didn't pick up the plugin's URL routes.

Checks:

1. Is the package installed in the CMS venv? ::

       tutor local run cms pip show course-inventory

2. Did Studio restart after install? Tutor's ``launch`` restarts; a
   bare ``tutor local exec`` or hot-reload may not.
3. Is the entry point registered? ::

       tutor local run cms python -c "from importlib.metadata import entry_points; \
                                       print([e for e in entry_points(group='cms.djangoapp')])"

   You should see ``course_inventory``.

4. Is the CMS process configured to load plugin apps? On stock Open
   edX this is the default; on heavily customized installs the plugin
   loader may be disabled.

``/course-inventory/`` returns 302 → admin/login
================================================

You're not logged in, or your user lacks ``is_staff=True``. The
dashboard intentionally does not allow non-staff access.

To grant access::

    tutor local run cms python manage.py cms shell -c \
      "from django.contrib.auth import get_user_model; \
       u=get_user_model().objects.get(username='alice'); \
       u.is_staff=True; u.save()"

``/course-inventory/`` returns 500
==================================

Capture the full traceback from the CMS logs. The most common causes:

* **Missing migrations.** Symptom: ``OperationalError: no such table:
  course_inventory_coursetag``. Run::

      tutor local run cms python manage.py cms migrate course_inventory

* **`django_htmx` not installed.** Symptom: template ``static`` tag
  can't find ``django_htmx/htmx.min.js``. The plugin settings hook
  should add it automatically; if you have a custom settings override
  that resets ``INSTALLED_APPS``, the hook may be skipped. Add
  ``"django_htmx"`` to ``INSTALLED_APPS`` manually.

* **Stale plugin module cache.** After a version upgrade, full
  process restart (not just touch-reload) is required.

Tags column doesn't update when I click ``+`` or ``x``
======================================================

Cause: HTMX isn't loading.

Checks:

1. View source on the inventory page. Confirm the ``<script
   src="…/static/django_htmx/htmx.min.js" …>`` tag is present.
2. Open browser DevTools → Network. The script should return 200.
3. If you see CSP violations in the console for ``script-src``,
   either your CSP excludes ``'self'`` (highly unusual) or staticfiles
   is serving from a different origin. Verify
   ``STATIC_URL`` / ``STATIC_HOST``.
4. Confirm the POST to ``/course-inventory/tag/<course_key>`` returns
   200 and not 403. If 403, your CSRF middleware may be stripping
   the cookie on this path. Verify the CSRF token is present in the
   form.

Export downloads truncated at 10,000 rows
=========================================

Working as configured. Raise
``COURSE_INVENTORY_EXPORT_MAX_ROWS`` (see :doc:`configuration`) if
you need bigger exports. Above ~100,000 rows you should be using a
proper analytics pipeline.

Search is slow on a large catalog
=================================

The listing query is one ``CourseOverview`` SELECT with two correlated
subqueries (``enrollment_count``, ``owner_count``). For >10K courses,
ensure:

* ``CourseOverview.org`` and ``CourseOverview.modified`` are indexed
  (they are in stock Open edX).
* You're not filtering by ``q`` with leading wildcards (the plugin
  uses ``icontains`` which is full-table on MySQL).

If a single column is consistently slow, look at the slow query log
to confirm the subqueries are using the right indexes.

A staff user can delete another user's tag
==========================================

By design — tags are a *shared* organizing layer (see
:doc:`tagging`). All mutations are logged at INFO with the acting
username; check your log aggregation for the audit trail.

How do I roll back?
===================

The plugin's three migrations are all reversible::

    tutor local run cms python manage.py cms migrate course_inventory zero

This drops ``course_inventory_coursetag`` and
``course_inventory_savedview``. The plugin reads no other tables, so
no other data is affected. After rollback, ``pip uninstall
course-inventory`` and rebuild the image.
