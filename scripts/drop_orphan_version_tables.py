"""Drop per-branch migration version tables whose branch catalog is gone.

    python3 scripts/drop_orphan_version_tables.py [--dry-run]

ci.yml's "Apply ddl" gives every non-main branch run its own version table by
exporting VERSION_TABLE_NAME_APPENDIX=_<slug>, so the engine records that branch's
revision in _spark_migrations_version_<slug>. Those tables do *not* live in the
branch's own catalog: the chain never issues `use catalog`, so the engine resolves
the name against the session's default catalog and schema. Dropping
<slug>_dbr_dbc_cat therefore leaves the version table behind, which is what this
collects.

The invariant it enforces: _spark_migrations_version_<slug> means something only
while <slug>_dbr_dbc_cat exists. Once the catalog is gone the recorded revision
describes nothing, and a branch that later reuses the slug (branch_slug.sh caps
slugs at 11 characters, so that happens) would read it and skip the whole chain
against a brand new catalog.

Sweeping rather than deleting one known name is deliberate: it also collects what
branches deleted before this existed left behind, and what a cleanup run that
failed halfway left behind. Nothing has to tell it where the tables are.

Every failure mode here can only under-delete. A catalog or schema this service
principal cannot read is reported and skipped, and a table is deleted only when
the catalog listing positively lacks its catalog -- a listing that fails aborts
the whole sweep rather than reading as "no catalogs exist".

Stdlib only, so it runs on any runner with a python3 and needs no Pants resolve.
Not a Pants target, like scripts/delete_ghcr_branch_tag.py. Auth comes from the
databricks CLI, which reads DATABRICKS_CLIENT_ID/SECRET/HOST from the environment.
"""

import json
import os
import re
import subprocess
import sys

# The engine's unsuffixed table name (spark_sql_migrations' get_version_table_name).
PREFIX = "_spark_migrations_version"
# main's own table is the bare PREFIX and is never a candidate: it tracks the
# shared dbr_dbc_cat, which no branch deletion may ever orphan.
# The branch catalog name "Apply ddl" builds, given a slug.
CATALOG_TEMPLATE = "{slug}_dbr_dbc_cat"
# What branch_slug.sh can emit, and so the only suffix shape trusted to name a
# catalog. Anything else is reported and left alone.
SLUG_RE = re.compile(r"[a-z0-9_]{1,11}")
# Not ours, and listing them tends to be refused outright.
SKIP_CATALOGS = {"system", "samples", "__databricks_internal"}
SKIP_SCHEMAS = {"information_schema"}


def cli(*args):
    """`databricks <args> -o json` as parsed json, or raise CalledProcessError."""
    done = subprocess.run(
        ["databricks", *args, "-o", "json"], capture_output=True, text=True, check=True
    )
    return json.loads(done.stdout) if done.stdout.strip() else []


def names(*args):
    return [entry["name"] for entry in cli(*args) if entry.get("name")]


def find_version_tables(catalogs):
    """every (catalog, schema, table) whose table name starts with PREFIX."""
    found = []
    for catalog in sorted(catalogs):
        if catalog in SKIP_CATALOGS:
            continue
        try:
            schemas = names("schemas", "list", catalog)
        except subprocess.CalledProcessError as err:
            print(f"cannot list schemas of {catalog}; skipping it: {err.stderr.strip()}")
            continue
        for schema in schemas:
            if schema in SKIP_SCHEMAS:
                continue
            try:
                tables = names("tables", "list", catalog, schema)
            except subprocess.CalledProcessError as err:
                print(f"cannot list tables of {catalog}.{schema}; skipping it: {err.stderr.strip()}")
                continue
            found.extend((catalog, schema, table) for table in tables if table.startswith(PREFIX))
    return found


def main(dry_run):
    catalogs = set(names("catalogs", "list"))
    if not catalogs:
        sys.exit("the catalog listing came back empty; refusing to sweep")

    for catalog, schema, table in find_version_tables(catalogs):
        full_name = f"{catalog}.{schema}.{table}"
        suffix = table[len(PREFIX) :]
        if not suffix:
            print(f"keeping {full_name}: the shared table, not a branch's")
            continue
        slug = suffix.removeprefix("_")
        if not SLUG_RE.fullmatch(slug):
            print(f"keeping {full_name}: {slug!r} is not a branch slug")
            continue
        branch_catalog = CATALOG_TEMPLATE.format(slug=slug)
        if branch_catalog in catalogs:
            print(f"keeping {full_name}: {branch_catalog} still exists")
            continue
        if dry_run:
            print(f"would drop {full_name}: no {branch_catalog}")
            continue
        cli("tables", "delete", full_name)
        print(f"dropped {full_name}: no {branch_catalog}")


if __name__ == "__main__":
    if [a for a in sys.argv[1:] if a != "--dry-run"]:
        sys.exit(f"usage: {os.path.basename(sys.argv[0])} [--dry-run]")
    main(dry_run="--dry-run" in sys.argv[1:])
