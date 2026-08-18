# ParqDB Demo

This repository deploys the official [ParqDB](https://github.com/parqdb-io/parqdb)
browser demo to [parqdb-io.github.io](https://parqdb-io.github.io/).

The site executes real vector queries in the browser. It discovers an immutable
package from `manifest.json`, reads selected Parquet byte ranges over HTTP, and
runs LVQ distance and top-k locally in WebAssembly. No query API or vector
database server is involved.

## Deployment

The Pages workflow builds a pinned ParqDB revision, packages the browser client,
WebAssembly kernel, and conformance fixtures, then deploys the static artifact
with GitHub Pages.

The ParqDB revision is intentionally immutable so the deployed client, package
format, and WebAssembly kernel cannot drift independently.
