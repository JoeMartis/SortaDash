=================================
tutor-contrib-course-inventory
=================================

A `Tutor <https://docs.tutor.edly.io/>`_ plugin that installs the
``course-inventory`` CMS plugin into an Open edX install and registers
its migrations.

Installation
============

::

    pip install tutor-contrib-course-inventory

Then enable the plugin and apply::

    tutor plugins enable course-inventory
    tutor config save
    tutor images build openedx   # rebuilds the openedx image with course-inventory pip-installed
    tutor local launch           # or `tutor dev launch`

Migrations run automatically during ``do init``. Visit
``https://studio.<your-domain>/course-inventory/`` as a staff user.

Configuration
=============

This plugin exposes the following Tutor config values
(see ``tutor config printvalue <KEY>``):

- ``COURSE_INVENTORY_VERSION`` — version reported by the plugin metadata.
- ``COURSE_INVENTORY_PIP_SPEC`` — exact pip requirement spec installed
  into the openedx image. Override to pin to a fork or a local
  source checkout, e.g.::

      tutor config save \
        --set COURSE_INVENTORY_PIP_SPEC='course-inventory @ git+https://github.com/your-fork/course-inventory@main'

License
=======

AGPL-3.0-or-later.
