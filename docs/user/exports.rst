=================
Exporting to CSV/TSV
=================

The dashboard streams the **current filtered view** to a CSV or TSV
file. The export reuses the same filter pipeline as the listing, so
whatever you see on the page is what gets exported.

Triggering an export
====================

On the inventory page, click **Export CSV** or **Export TSV** in the
searchbar. The browser downloads a file named
``course-inventory.csv`` or ``course-inventory.tsv``.

Columns
=======

The columns are fixed::

    course_id, display_name, org, start, end, pacing, visibility,
    modified, enrollment_count, owner_count

* ``start``, ``end``, ``modified`` are ISO 8601.
* ``pacing`` is ``self`` or ``instructor``.
* ``enrollment_count`` and ``owner_count`` are integers.

Size cap and truncation
=======================

The export is hard-capped at
``COURSE_INVENTORY_EXPORT_MAX_ROWS`` (default **10,000** rows). Above
the cap, the stream ends with a single trailer row::

    __TRUNCATED__ at 10000 rows; narrow your filters and re-export

The file remains well-formed CSV/TSV. To raise the cap, see
:doc:`configuration`.

Formula-injection safety
========================

CSV cells beginning with ``=``, ``+``, ``-``, ``@``, ``\t``, or ``\r``
are auto-prefixed with a single quote (``'``) before being written.
This neuters Excel and Google Sheets formula evaluation on a
malicious ``display_name`` (e.g. ``=HYPERLINK("http://evil","click")``).

The prefix is visible when the cell is opened as text. Tools that
strip it on load will see the original value.

Streaming
=========

The export streams row-by-row using
``django.http.StreamingHttpResponse``. There is no buffer of the full
result set in memory. The DB iterator chunk size is set by
``COURSE_INVENTORY_EXPORT_CHUNK_SIZE`` (default 500).

URL form
========

The URL is ``/course-inventory/export?format=csv|tsv&<filters>``. The
``<filters>`` portion is exactly the same querystring the inventory
listing uses, so you can build export URLs programmatically.

What's NOT in the export
========================

* Tags. The export is per-course; the relationship to ``CourseTag``
  is many-to-many. Use Django admin or the shell if you need a flat
  list of tags.
* Owner usernames. ``owner_count`` is included; usernames are not.
* Modulestore content. The plugin never reads the modulestore.
