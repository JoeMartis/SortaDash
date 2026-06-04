=======
Testing
=======

The test suite is pytest-based, runs in-process against an in-memory
SQLite, and **does not require ``edx-platform`` to be installed**.

Running the suite
=================

::

    pip install -e ".[test]"
    pip install -e ./tutor-plugin    # optional, for Tutor smoke tests
    pytest

With coverage::

    pytest --cov --cov-report=term-missing

The coverage gate in CI is **85%**. Local default is the same.

How the stub layer works
========================

``services.py`` lazily imports three ``edx-platform`` models:

* ``CourseOverview`` from
  ``openedx.core.djangoapps.content.course_overviews.models``
* ``CourseEnrollment`` from ``common.djangoapps.student.models``
* ``CourseAccessRole`` from ``common.djangoapps.student.models``

In production those imports resolve against the real platform. Under
test we shim them via a tiny Django app and namespace packages.

::

    tests/
      stubs/
        models.py            # real Django models, app_label="stubs"
      openedx/
        core/djangoapps/content/course_overviews/
          models.py          # re-exports stubs.models.CourseOverview
      common/
        djangoapps/student/
          models.py          # re-exports CourseEnrollment, CourseAccessRole

``tests/`` is added to ``sys.path`` via the pytest ``pythonpath``
setting in ``pyproject.toml``, so the ``openedx.*`` and ``common.*``
namespace packages are findable. ``services._lazy_imports()`` then
picks up the stubs naturally — no monkeypatching required.

Why stubs aren't a real platform install
----------------------------------------

* Pulling ``edx-platform`` into a unit-test venv is a multi-gigabyte
  download with conflicting dependencies and a 10-minute install.
* The stubs are exactly the field subset the plugin actually reads,
  and they live in one file (``tests/stubs/models.py``). When the
  plugin starts reading a new field, the stub gains a field at the
  same time — easy to grep.
* Tests can construct fake courses, enrollments, and roles with
  plain ``Model.objects.create(...)`` and exercise real Django ORM
  semantics.

Caveat: stub fidelity
---------------------

The stub ``CourseOverview.modified`` uses ``auto_now=True`` to mirror
production. That means setting ``modified=...`` on ``create()`` is a
no-op — Django overwrites on save. The ``make_course`` fixture
handles this by calling ``.update(modified=...)`` after the row
exists. If you find yourself testing a model field where the stub
doesn't match production behavior, fix the stub first and document
the assumption.

Fixtures
========

In ``tests/conftest.py``:

* ``staff_user`` / ``regular_user`` — pre-saved auth users.
* ``make_course`` — factory for ``CourseOverview`` rows.
* ``enroll`` — factory for ``CourseEnrollment``.
* ``add_role`` — factory for ``CourseAccessRole`` (defaults to
  ``instructor``).

Test layout
===========

::

    tests/
      conftest.py            # fixtures
      settings.py            # the pytest-django settings module
      urls.py                # routes course_inventory under /course-inventory/
      templates/base.html    # CMS base.html shim
      stubs/                 # see above
      openedx/, common/      # namespace shims
      test_models.py         # CourseTag + SavedView constraints
      test_services.py       # base_queryset + helpers
      test_filters.py        # parse + apply + sanitize_filters
      test_view_helpers.py   # _page_decorations, _sanitize_csv_cell
      test_views.py          # end-to-end via Django test client
      test_templatetags.py   # qs_replace, qs_toggle, build_qs, course_dom_id
      test_migrations.py     # forward → zero → forward
      test_plugin_settings.py
      test_tutor_plugin.py   # importorskip if tutor isn't installed

Patterns we use
===============

* **End-to-end view tests use ``client.force_login(user)``**, not
  the auth middleware path. Faster and side-steps middleware
  ordering.
* **Tests that exercise HTMX paths set the header explicitly**:
  ``client.get(url, headers={"HX-Request": "true"})``.
* **Tests that need a non-now ``modified``** call ``.update()`` via
  the ``make_course`` fixture.
* **Tests that exercise the Tutor plugin** are guarded by
  ``pytest.importorskip("tutor")`` so the suite still runs in a venv
  without the Tutor plugin installed.

Adding a test
=============

Aim for a test per filter branch, per view code path, and per security
boundary. A new feature should land with at least:

1. A model / services test exercising the new ORM behavior.
2. A filter / parse test if it touches the querystring schema.
3. An end-to-end view test confirming the response (status + content
   substring).
4. If user-visible: a templatetag or template test if there's a
   nontrivial rendering branch.

CI matrix
=========

``.github/workflows/ci.yml`` runs:

* ``lint`` — ``ruff check`` + ``ruff format --check``.
* ``test`` — pytest matrix on Python 3.11 / 3.12 × Django 4.2 / 5.2,
  with coverage gate.
* ``build`` — ``python -m build`` on both packages.
* ``audit`` — ``pip-audit`` against runtime deps.

Tooling drift between ``tox.ini`` and CI is intentionally minimal;
``make check`` runs the same commands locally.
