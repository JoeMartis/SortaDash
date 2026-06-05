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

Scale tests
===========

``tests/test_scale.py`` seeds a 1,000-course catalog and asserts the
plugin's query budget stays constant:

* ``base_queryset()`` resolves to a single SELECT.
* ``_page_decorations(page)`` is exactly two queries (owners + tags).
* The end-to-end listing view stays under 8 plugin queries.
* The same budget holds with every filter applied.

These tests cost ~30 seconds because of the fixture seed. They run
in the same suite as everything else; if you want to skip them
locally::

    pytest --deselect tests/test_scale.py

If a future change introduces an N+1 or a per-row query, the
query-count budget breaks and these tests fail loudly.

Tutor end-to-end smoke
======================

For real CMS integration coverage that unit tests can't provide,
``scripts/tutor_smoke.sh`` is a runnable harness that builds the
openedx image with the plugin pip-installed, launches a Tutor stack,
seeds a staff user and a fake ``CourseOverview`` row, and (intends
to) drive ``GET /course-inventory/`` as that user.

It runs in CI behind a manual ``workflow_dispatch`` trigger in
``.github/workflows/tutor-smoke.yml`` — expensive (~20 minutes per
run) so we don't gate every PR on it. Run before a release, when
touching ``tutor-plugin/``, or when a reviewer asks for CMS
integration evidence.

Locally::

    ./scripts/tutor_smoke.sh                  # build, launch, test, teardown
    KEEP_RUNNING=1 ./scripts/tutor_smoke.sh   # leave the stack up
    PLUGIN_SOURCE=git ./scripts/tutor_smoke.sh  # install from PyPI, not source

You'll need Tutor 21+, Docker, ~8 GB RAM, ~20 GB disk for the
openedx image, and a few patient minutes.

Current state (be honest with reviewers)
----------------------------------------

The harness was iterated extensively during v0.1.0 development. It
successfully validates **seven of eight phases** of end-to-end
integration with a real Open edX install:

1. Plugin pip-installs into a real openedx Docker image build.
2. The Tutor companion plugin's three hook registrations
   (``CONFIG_DEFAULTS``, ``ENV_PATCHES``, ``CLI_DO_INIT_TASKS``)
   fire correctly when Tutor loads it.
3. Our ``CLI_DO_INIT_TASKS`` runs the plugin's migrations during
   ``tutor local launch``.
4. The plugin loads in the openedx Python process with no
   ``AppConfig`` conflicts and no platform-side import errors.
5. The plugin's URL routes (``/course-inventory/``) are reachable
   through Caddy, with correct ``Host``-header routing to the CMS
   upstream.
6. The ``@staff_member_required`` decorator fires correctly
   (verified: unauthenticated requests get a 302 to
   ``/admin/login/``).
7. A viable ``CourseOverview`` row insert triggers the platform's
   own ``IMPORT_COURSE_DETAILS`` post-save signal — the platform
   itself acknowledges our plugin's data.

The remaining phase — **injecting a pre-authenticated session into
Open edX's** ``SafeSessionMiddleware`` **chain** so curl can drive
the dashboard as a staff user — was not solved end-to-end. Open edX
wraps Django's stock ``SessionMiddleware`` with
``SafeSessionMiddleware``, which expects an HMAC-signed cookie
envelope of the form ``<session_id>|<user_id>|<signature>`` rather
than the raw session key. Constructing that envelope from outside
the running CMS requires the platform-private ``SafeCookieData``
helper, whose API surface is not stable across releases.

Closing the gap is **explicitly out of scope** for this smoke test:
it's a harness implementation detail, not a plugin concern. The
seven-phase validation above is what carries the actual integration
signal — the plugin demonstrably loads, registers, migrates, and
serves through Caddy in a real CMS, alongside the platform itself
recognizing our data.

During development the harness also surfaced **seven real
integration findings** that pure unit tests could not have caught
(the openedx Dockerfile build-context layout, ``manage.py``'s
required ``lms``/``cms`` subcommand, ``CourseOverview.version`` as
a NOT NULL field without a default, Tutor's ``http://`` -only
exposure without ``/etc/hosts`` entries, Open edX's redirect chain
for ``/admin/login/``, Django 4.1+ session-auth-hash requirements,
and ``SafeSessionMiddleware`` itself). That iteration history is
part of the artifact's value, regardless of whether the eighth
phase ever lands.

If you want to push past the gap
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Two viable paths:

* Replace the ``SafeCookieData.create()`` invocation in
  ``scripts/tutor_smoke.sh`` with whatever your target Open edX
  release's session-cookie API exposes, then re-run.
* Or replace the curl assertions entirely with a Django management
  command that renders the view via the test client
  (``django.test.Client.force_login`` understands the platform's
  full middleware stack) and asserts on the response. This
  sidesteps the cookie layer.

