============
Contributing
============

Thanks for your interest in ``course-inventory``! This document covers
the mechanics. For the why behind the design see the architecture
notes in ``README.rst`` and ``CHANGELOG.rst``.

Local development
=================

::

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    pip install -e ./tutor-plugin    # only needed for tutor tests
    pre-commit install

Common targets via ``make``::

    make test         # pytest with coverage
    make lint         # ruff check
    make format       # ruff format
    make check        # lint + format check + tests + makemigrations check
    make build        # sdist + wheel for both packages
    make clean

Tests
=====

::

    pytest

The suite ships with a small Django app under ``tests/stubs/`` that
stands in for the edx-platform models the plugin reads, plus
namespace-package shims under ``tests/openedx/`` and ``tests/common/``
so ``services.py`` lazy imports resolve. No edx-platform install is
required.

Coverage gate is 85%. The CI matrix runs on Python 3.11 / 3.12 and
Django 4.2 / 5.2.

Style
=====

``ruff`` for lint + format. Pre-commit hooks enforce the same rules
locally as CI. Code targets Python 3.11+.

Branch and PR conventions
=========================

* Branch off ``main``.
* Keep PRs focused; smaller is better.
* Update ``CHANGELOG.rst`` (Unreleased section).
* If a behavior change has a security or migration impact, call it out
  in the PR description and the changelog.

Security
========

If you find a security issue, please email the maintainers privately
rather than opening a public issue. See `the Open edX disclosure
process <https://openedx.org/security>`__.

Code of conduct
===============

This project follows the
`Open edX Code of Conduct
<https://openedx.org/code-of-conduct/>`__.
