---
pagefind: false
banner:
  content: 'You are viewing the ParqDB 0.2 documentation snapshot. <a href="/docs">Read the latest documentation →</a>'
title: Versions and compatibility
description: Understand documentation snapshots, package releases, catalog metadata, and index format versions.
---

ParqDB is pre-release software. The project versions its Python package, public
documentation, catalog schema, transport protocol, and persisted index formats
independently because they change on different schedules.

## Documentation versions

- [`/docs`](/docs) follows the current development and release line.
- [`/docs/0.2`](/docs/0.2) is the preserved 0.2 documentation snapshot.

Use the version selector in the documentation sidebar to keep an equivalent
page open when switching versions. Search indexes only the latest
documentation, so an old page cannot silently outrank current guidance.

## Package releases

Python package versions identify installable releases. Pin an exact pre-release
in reproducible environments and review the
[GitHub release notes](https://github.com/parqdb-io/parqdb/releases) before
upgrading. The latest development documentation can describe changes that are
not present in an older installed wheel.

## Persisted format versions

Format numbers are not package versions:

- SQLite `user_version` identifies the embedded catalog schema.
- `format-version` identifies an immutable metadata document.
- `index-schema-version` identifies the logical schema and semantics of an
  index family.
- HTTP protocol and browser manifest versions identify their own wire formats.

A value such as `format-version = 1` does not mean ParqDB 1.0. Readers validate
each format at its boundary and reject an unsupported version instead of
guessing.

The normative contracts live in the
[open index specification](/docs/0.2/spec).
RFCs explain proposed designs but are not compatibility promises until their
behavior is implemented, tested, and documented.

## Before upgrading

1. Pin the package version used by production and index builders.
2. Read the release notes and any breaking-change marker.
3. Test reopening the catalog and querying representative existing indexes.
4. Re-run recall, latency, and I/O checks when index construction or query
   planning changes.
5. Keep source data and immutable index objects recoverable until validation
   completes.

Pre-release upgrades may require a rebuild or migration. Do not infer
compatibility from a shared major version alone; use the release notes and
persisted-format specifications.
