============
Installation
============

``course-inventory`` is a standard Open edX Django plugin app. It
self-registers via the ``cms.djangoapp`` entry point, so no edits to
``edx-platform`` are required.

It is known to work on Open edX **Sumac** and **Teak**, and on the
``master`` branch.

Pick the install path that matches your deployment.

Tutor (recommended)
===================

Two options. The first is fast; the second handles migrations
automatically and is what we recommend for production.

Option 1: pip-only
------------------

Add the package to ``OPENEDX_EXTRA_PIP_REQUIREMENTS`` and rebuild the
openedx image::

    tutor config save --append OPENEDX_EXTRA_PIP_REQUIREMENTS=course-inventory
    tutor images build openedx
    tutor local launch

Run migrations once::

    tutor local run cms python manage.py cms migrate course_inventory

Option 2: Tutor plugin (auto migrations)
----------------------------------------

Install the companion Tutor plugin. It adds the pip dependency and
runs migrations during ``tutor … do init``::

    pip install tutor-contrib-course-inventory
    tutor plugins enable course-inventory
    tutor config save
    tutor images build openedx
    tutor local launch

To install the Tutor plugin from this repository::

    pip install ./tutor-plugin

The Tutor plugin's source lives in ``tutor-plugin/``.

Native (no Tutor)
=================

Install into the CMS Python environment::

    pip install course-inventory

Run migrations::

    ./manage.py cms migrate course_inventory

Restart the CMS process so the plugin's URL routes and settings hook
take effect.

Verifying the install
=====================

1. Confirm the plugin is discovered::

       python -c "from importlib.metadata import entry_points; \
                  print([e for e in entry_points(group='cms.djangoapp')])"

   You should see an entry point named ``course_inventory``.

2. Visit ``https://studio.<your-domain>/course-inventory/`` as a user
   with ``is_staff=True``.

3. If you see an empty listing on a brand-new install, that's expected
   — there are no courses yet.

Next steps
==========

* :doc:`quickstart` — what staff users do on the dashboard.
* :doc:`configuration` — tunables and when to override them.
* :doc:`troubleshooting` — common install issues.
