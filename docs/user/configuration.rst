=============
Configuration
=============

All plugin settings are optional. Defaults are applied by the plugin
``settings/common.py`` hook, which edx-platform invokes during CMS
startup. Override in your environment-specific settings module (e.g.
``cms/envs/production.py``) or via a Tutor patch.

Reference
=========

================================================  =========  ==========================================
Setting                                            Default    Purpose
================================================  =========  ==========================================
``COURSE_INVENTORY_PAGE_SIZE``                     ``50``     Rows per page on the listing.
``COURSE_INVENTORY_EXPORT_CHUNK_SIZE``             ``500``    DB iterator chunk size for CSV/TSV
                                                              streaming export. Larger = fewer DB
                                                              round-trips, more memory.
``COURSE_INVENTORY_EXPORT_MAX_ROWS``               ``10000``  Hard cap on export rows. Above the cap
                                                              the stream emits a ``__TRUNCATED__``
                                                              trailer.
``COURSE_INVENTORY_TAG_KEYS``                      ``["lifecycle", "team", "program", "term"]``
                                                              Suggestion list shown in the inline-tag
                                                              datalist. Operators can add any keys at
                                                              runtime; this only controls autosuggest.
================================================  =========  ==========================================

When to override
================

Large catalogs
--------------

For installs with 5,000+ courses, consider:

* Raising ``COURSE_INVENTORY_PAGE_SIZE`` to 100–200 so staff scroll
  less.
* Raising ``COURSE_INVENTORY_EXPORT_MAX_ROWS`` if your operators
  routinely need full-catalog exports. Be aware that very large CSVs
  exhaust browser memory on open; consider an async export pipeline
  instead.

Restrictive CSP
---------------

The plugin ships HTMX as a same-origin static asset (via
``django-htmx``). No additional CSP header changes should be needed.

Custom tag autocomplete
-----------------------

To surface a different starter list of keys::

    COURSE_INVENTORY_TAG_KEYS = ["status", "audience", "fiscal_year"]

This affects only the autocomplete datalist; the data model accepts
any key.

Tutor overrides
===============

Inside a Tutor plugin, set these via a CMS settings patch. Example
``plugin.py``::

    hooks.Filters.ENV_PATCHES.add_item(
        (
            "openedx-cms-production-settings",
            "COURSE_INVENTORY_EXPORT_MAX_ROWS = 50000",
        )
    )

The Tutor companion plugin (``tutor-contrib-course-inventory``) also
exposes ``COURSE_INVENTORY_VERSION`` and ``COURSE_INVENTORY_PIP_SPEC``
config values; see ``tutor-plugin/README.rst``.

Per-environment guidance
========================

Development
-----------

Defaults are fine. The dev workflow assumes small fixture catalogs.

Staging
-------

Match production. Use stage to validate the export cap; raise if your
QA team complains it truncates legit jobs.

Production
----------

Set ``COURSE_INVENTORY_EXPORT_MAX_ROWS`` to a value your DB and
network can comfortably stream — a 50K-course export is a multi-MB
file and a non-trivial DB scan. If you find staff hitting the cap
regularly, that's a signal to look at filtered exports or a separate
analytics pipeline.

Settings the plugin does NOT read
=================================

For clarity, the plugin does not read:

* ``CMS_BASE`` / ``LMS_BASE`` (it lives entirely inside CMS).
* Any course-content settings (it never touches the modulestore).
* Any caching settings — it relies on the host's defaults.

Verifying your overrides
========================

In a Django shell::

    >>> from django.conf import settings
    >>> settings.COURSE_INVENTORY_EXPORT_MAX_ROWS
    50000
