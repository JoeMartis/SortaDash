=================
Release process
=================

The plugin follows `Semantic Versioning <https://semver.org/>`__ and
`Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`__.

Two packages, one version
=========================

The repo ships two pip packages that always share a version:

* ``course-inventory`` — the CMS plugin app.
  Version source: ``course_inventory/__init__.py``.
* ``tutor-contrib-course-inventory`` — the Tutor companion plugin.
  Version source: ``tutor-plugin/tutorcourseinventory/__about__.py``.

The companion plugin's ``COURSE_INVENTORY_PIP_SPEC`` default points at
the matching main-package version, so a mismatch breaks Tutor
installs. ``make check`` cross-checks the two ``__version__`` strings
and fails fast on drift.

Cutting a release
=================

1. **Pick the bump.**

   * Patch (``0.1.0`` → ``0.1.1``): bug fixes, doc-only changes.
   * Minor (``0.1.0`` → ``0.2.0``): new features, new settings, new
     migrations. Backward-compatible.
   * Major (``0.x`` → ``1.0``): API or migration changes that
     require operator action.

2. **Bump both ``__version__`` strings** to the new value::

       sed -i 's/__version__ = "0.1.0"/__version__ = "0.1.1"/' \
         course_inventory/__init__.py \
         tutor-plugin/tutorcourseinventory/__about__.py

3. **Move ``Unreleased`` to the new version** in ``CHANGELOG.rst``,
   under the bump number with the date.

4. **Run the full check::

       make check

5. **Build the wheels and sdists**::

       make build

   Artifacts land in ``dist/`` and ``tutor-plugin/dist/``.

6. **Open a PR.** Title format: ``Release v0.1.1``.

7. **After merge, tag and push**::

       git tag -s v0.1.1 -m "course-inventory v0.1.1"
       git push origin v0.1.1

   GPG sign the tag if your contributor agreement permits.

8. **Publish** (maintainers only)::

       twine upload dist/*
       twine upload tutor-plugin/dist/*

9. **Verify on PyPI** that both packages are installable::

       pip install course-inventory==0.1.1
       pip install tutor-contrib-course-inventory==0.1.1

Hotfixes
========

For a security or crash fix that must ship out-of-cycle:

1. Branch from the previous release tag (e.g. ``git checkout -b
   hotfix/0.1.2 v0.1.1``).
2. Cherry-pick the fix.
3. Cut a patch release as above.
4. Forward-merge ``hotfix/0.1.2`` back into ``main``.

Migration policy
================

* Every migration must be reversible. ``test_course_inventory_migrations_reversible``
  enforces this in CI.
* Schema-changing migrations bump at minimum a *minor* version and are
  called out in the changelog.
* Backfills that take more than ~30s on a 5k-course install must ship
  with operator-runnable management commands, not as part of the
  migration itself.

Deprecating a setting
=====================

If a configuration key is being renamed or removed:

1. Add the new key alongside the old in
   ``settings/common.py``.
2. Log a ``DeprecationWarning`` from ``plugin_settings`` when the old
   key is set.
3. Document the deprecation in ``CHANGELOG.rst`` (Deprecated
   section).
4. Remove the old key in the next major release.

Communication
=============

* Announce on the `Open edX discussion forum
  <https://discuss.openedx.org/>`__ with a link to the changelog
  entry.
* If the release contains a security fix, follow the Open edX
  responsible-disclosure process before opening the PR.
