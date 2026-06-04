# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Migration smoke tests.

These run the plugin's migrations forward and back to make sure they
are reversible — operators who roll back a release must be able to
unmigrate without manual SQL surgery.
"""

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_course_inventory_migrations_reversible():
    """Forward to head, back to zero, forward to head again."""
    executor = MigrationExecutor(connection)
    head = [m for m in executor.loader.graph.leaf_nodes() if m[0] == "course_inventory"]
    assert head, "course_inventory has no migrations"
    target = head[0]

    # Roll back to zero, then forward, then verify head reached.
    call_command("migrate", "course_inventory", "zero", verbosity=0)
    call_command("migrate", "course_inventory", target[1], verbosity=0)

    executor.loader.build_graph()
    applied = {m for m in executor.loader.applied_migrations if m[0] == "course_inventory"}
    assert target in applied
