"""Delete a deleted branch's pre-migrated Spark image tag from GHCR.

    GITHUB_TOKEN=... python3 scripts/delete_ghcr_branch_tag.py <owner> <slug> [--dry-run]

GHCR has no "untag" call: the Packages API only deletes whole package versions
(one per image digest), and a version can carry several tags. So a version is
deleted only when <slug> is its *sole* tag. One that also carries `latest`, or
another branch's slug, is left alone and reported -- deleting it would silently
take those tags down with it.

Stdlib only, so it runs on any runner with a python3 and needs no Pants resolve.
Not a Pants target, like docker/spark-migrated/register_tables.py.
"""

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
# Must match GHCR_IMAGE's default in scripts/build_migrated_image.sh.
PACKAGE = "cms-pipeline-spark-migrated"
# Tags a branch deletion must never remove, even if one somehow maps to a slug.
PROTECTED_TAGS = {"latest", "main"}


def api(method, path, token):
    request = urllib.request.Request(
        f"{API}{path}",
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request) as response:
        body = response.read()
    return json.loads(body) if body else None


def owner_packages_path(owner, token):
    # User- and org-owned packages live under different API roots.
    kind = api("GET", f"/users/{owner}", token)["type"]
    return f"/{'orgs' if kind == 'Organization' else 'users'}/{owner}/packages/container/{PACKAGE}"


def list_versions(base, token):
    versions, page = [], 1
    while True:
        batch = api("GET", f"{base}/versions?per_page=100&page={page}", token)
        versions.extend(batch)
        if len(batch) < 100:
            return versions
        page += 1


def main(owner, slug, dry_run):
    if slug in PROTECTED_TAGS:
        sys.exit(f"refusing to delete protected tag {slug!r}")
    token = os.environ["GITHUB_TOKEN"]

    base = owner_packages_path(owner, token)
    try:
        versions = list_versions(base, token)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            print(f"no {PACKAGE} package under {owner}; nothing to clean up")
            return
        raise

    tagged = [v for v in versions if slug in v["metadata"]["container"]["tags"]]
    if not tagged:
        print(f"no {PACKAGE} version tagged {slug!r}; nothing to clean up")
        return

    for version in tagged:
        tags = version["metadata"]["container"]["tags"]
        if tags != [slug]:
            print(f"keeping {version['name']}: also tagged {sorted(set(tags) - {slug})}")
            continue
        if dry_run:
            print(f"would delete {version['name']} (tag {slug!r})")
            continue
        api("DELETE", f"{base}/versions/{version['id']}", token)
        print(f"deleted {version['name']} (tag {slug!r})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if len(args) != 2:
        sys.exit(f"usage: {os.path.basename(sys.argv[0])} <owner> <slug> [--dry-run]")
    main(*args, dry_run="--dry-run" in sys.argv[1:])
