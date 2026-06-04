==========================
Extending the plugin
==========================

v1 deliberately ships no extension hook. The audience is small and
the surface is narrow; we'd rather pull patterns up from real fork
needs than guess. If you need an extension point, please open an
issue describing the use case.

In the meantime, every common change is one or two file edits.

Add a new facet
===============

Suppose you want a **language** facet driven by
``CourseOverview.language``.

1. **Schema for the filter dict** — register the key in
   ``filters.py`` ``_SCHEMA`` so ``sanitize_filters`` accepts it::

       _SCHEMA = {
           ...,
           "language": "list",
       }

2. **Parsing** — add to ``parse()``::

       "language": get.getlist("language"),

3. **Application** — add a block in ``apply()``::

       if filters["language"]:
           qs = qs.filter(language__in=filters["language"])

4. **Facet helper** — if you need a values-list for the panel, add to
   ``services.py``::

       def distinct_languages() -> list[str]:
           CourseOverview, _ce, _car = _lazy_imports()
           return list(
               CourseOverview.objects.exclude(language="")
               .order_by("language")
               .values_list("language", flat=True).distinct()
           )

5. **View** — pass it to the template context in
   ``views.inventory_list``::

       "languages": services.distinct_languages(),

6. **Template** — drop a fieldset into ``_facet_panel.html``::

       <fieldset>
         <legend>{% trans "Language" %}</legend>
         {% for lang in languages %}
           <label>
             <input type="checkbox" name="language" value="{{ lang }}"
                    {% if lang in filters.language %}checked{% endif %} />
             {{ lang }}
           </label>
         {% endfor %}
       </fieldset>

7. **Test** — mirror ``test_filter_by_org`` in ``test_filters.py``.

Add a new column to the listing
===============================

Edit ``_table.html`` (header) and ``_row.html`` (body). If the column
is sortable, add the field to ``filters.SORTABLE`` and add an
``aria-sort``-aware ``<th>`` linking to ``qs_replace``.

Add a new column to the export
==============================

Edit ``views.export`` — both the ``columns`` list and the per-row
``writer.writerow([...])`` body. Wrap any operator-controlled string
with ``_sanitize_csv_cell`` to keep formula-injection safety.

Change tag-key autocomplete
===========================

Override ``COURSE_INVENTORY_TAG_KEYS`` (see
:doc:`/user/configuration`). The data model accepts any key
unconditionally; the setting only changes what the autocomplete
suggests.

Change the owner-role list
==========================

Right now ``services.OWNER_ROLES`` is hard-coded to
``("instructor", "staff")``. To honor a deployment-specific role like
``"limited_staff"``:

Option A: monkeypatch in your own plugin's settings hook (cheap,
unobtrusive)::

    from course_inventory import services
    services.OWNER_ROLES = ("instructor", "staff", "limited_staff")

Option B: open a PR to make this configurable via
``COURSE_INVENTORY_OWNER_ROLES``.

Add a destructive action (e.g. bulk archive)
============================================

v1 is read-and-organize only. If you must extend with a destructive
action:

1. **Stop and reconsider.** The design doc lists destructive
   operations as an explicit non-goal for v1 specifically because of
   the mis-scoping risk on a 400-course catalog.
2. If you proceed, gate it behind a **separate** permission check
   (not ``staff_member_required``), require a confirmation token in
   the URL, log the action at ``WARNING`` with the full filter dict,
   and never expose it through a GET request.
3. Add a test asserting it's a 405 on GET.

Customize the UI
================

The templates extend ``cms/templates/base.html`` so they inherit
Studio's chrome. Override any template by shadowing its path in your
own app's templates directory and listing your app *before*
``course_inventory`` in ``INSTALLED_APPS``.

Add a translation
=================

From the package root::

    cd course_inventory
    django-admin makemessages -l fr

Edit the resulting ``locale/fr/LC_MESSAGES/django.po`` and commit it.
Then::

    django-admin compilemessages

Open a PR.

When to fork vs PR
==================

* **Single-deployment quirk** (you only need it for your install) →
  monkeypatch in your settings hook, or fork.
* **Generic improvement** that other operators would also want → PR.
* **Reshape of v1 scope** (destructive actions, MFE, etc.) → open
  an issue first; the maintainers will tell you whether the scope
  change is welcome.
