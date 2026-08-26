---
title: Run a server
description: Start and verify the experimental ParqDB HTTP server, then build and query an index through Arrow IPC.
banner:
  content: 'You are viewing the ParqDB 0.3 documentation snapshot. <a href="/docs">Read the latest documentation →</a>'
---

:::caution[Experimental]
The HTTP server is experimental. The embedded DataFusion runtime is the first supported product surface.
:::

The ParqDB server exposes the same table, index, vector-query, and SQL APIs as
an embedded session over HTTP. It is experimental and currently runs as one
process with one ASGI worker.

## Install and Start

Install ParqDB in the process that will own the catalog, index data, and
storage credentials:

```bash
python -m pip install parqdb
mkdir parqdb-service
cd parqdb-service
parqdb config init
parqdb serve
```

`parqdb config init` writes `parqdb.toml`. `parqdb serve` loads that file from
the current directory by default. Without a file, it starts with the same
safe defaults and prints how to materialize the template.

The default configuration listens only on `127.0.0.1:8000`, stores persistent
state in `./parqdb`, and permits no remote source registration:

```toml
[server]
root = "./parqdb"
host = "127.0.0.1"
port = 8000
allowed_source_prefixes = []

[storage]

[session]
```

Set `allowed_source_prefixes` before clients register Parquet sources. Paths
are resolved relative to `parqdb.toml`; object-store prefixes remain URIs:

```toml
[server]
root = "./parqdb"
host = "0.0.0.0"
port = 8000
allowed_source_prefixes = [
  "/srv/lakehouse/documents",
  "s3://company-data/documents",
]

[storage]
aws_region = "us-east-1"

[session]
"parqdb.execution.query_dop" = "8"
"parqdb.execution.query_concurrency" = "16"
```

Keep cloud credentials in the server process environment or its credential
provider, rather than in `parqdb.toml`.

To use a different location, pass it explicitly:

```bash
parqdb serve --config /etc/parqdb/parqdb.toml
```

## Verify the Service

Keep the server running and use a second terminal. First verify that the HTTP
process is reachable:

```bash
curl --fail --silent http://127.0.0.1:8000/health
```

The response must be:

```json
{"status":"ok"}
```

The health endpoint does not execute a query. Run a constant SQL query to also
verify the Python client, HTTP transport, server runtime, and Arrow IPC result
stream:

```bash
python - <<'PY'
import parqdb

with parqdb.connect("http://127.0.0.1:8000") as session:
    result = session.sql("SELECT 1 AS ready")
    assert result.to_pylist() == [{"ready": 1}]
    print(result.to_pylist())
PY
```

Expected output:

```text
[{'ready': 1}]
```

Install the same ParqDB pre-release in the client and server environments.
Cross-version client/server compatibility is not yet a stable guarantee.

## Build and Query an Index

The client uses the normal session facade. Registered paths are resolved on the
server and are never uploaded from the client. The following example assumes
the server can read the configured `/srv/lakehouse/documents/*.parquet` source.
Replace the field names, query dimension, and index settings for your table:

```python
from datetime import timedelta

import parqdb

with parqdb.connect("http://127.0.0.1:8000") as session:
    session.register_parquet(
        "documents",
        "/srv/lakehouse/documents/*.parquet",
    )
    documents = session.table("documents")
    print(documents.schema)

    documents.create_index(
        "documents_embedding",
        column="embedding",
        key=["document_id"],
        config=parqdb.IVF(
            nlist=4096,
            encoding="lvq8",
            metric="cosine",
        ),
    )
    documents.wait_for_index(
        "documents_embedding",
        timeout=timedelta(hours=1),
    )

    status = documents.index_status("documents_embedding")
    assert status.state == "ready"
    print("index:", status.state, status.current_snapshot_id)

    query_vector = [0.2, 0.0]  # Replace with one model-compatible vector.
    query = (
        documents.search(
            query_vector,
            column="embedding",
            index="documents_embedding",
        )
        .nprobes(64)
        .limit(10)
        .select(["document_id", "title"])
    )
    hits = session.collect(query)
    print(hits.to_pylist())
```

`nlist` must not exceed the source row count. Use the
[IVF tuning guide](/docs/0.3/guides/index-tuning) rather than copying `4096` as a
universal default.

The result contains the selected source fields followed by `_distance`, with
smaller values ranked first. `create_index` submits a server-side build;
`wait_for_index` polls until the immutable snapshot is ready or the timeout is
reached. Reconnecting does not require registration again because the table and
published index are stored in the server catalog.

To query an index that is already present after a reconnect:

```python
import parqdb

query_vector = [0.2, 0.0]  # Same dimension and embedding model as the source.
with parqdb.connect("http://127.0.0.1:8000") as session:
    documents = session.table("documents")
    print(documents.list_indexes())
    hits = session.collect(
        documents.search(query_vector, index="documents_embedding")
        .nprobes(64)
        .limit(10)
        .select(["document_id", "title"])
    )
    print(hits.to_pylist())
```

## Inspect and Diagnose

Verify that the index appears in the catalog, then inspect the plan and actual
operator metrics:

```python
import parqdb

with parqdb.connect("http://127.0.0.1:8000") as session:
    documents = session.table("documents")
    query = (
        documents.search([0.2, 0.0], index="documents_embedding")
        .nprobes(64)
        .limit(10)
    )
    print(session.list_tables())
    print(documents.list_indexes())
    print(session.explain(query))
    print(session.analyze(query))
```

The machine-readable HTTP contract is available at
`http://127.0.0.1:8000/openapi.json`.

If `/health` fails, check the listen address, port, and server process. If SQL
fails, inspect the server log because that path exercises query execution and
Arrow IPC. A rejected registration usually means the path is not visible to
the server or is outside `allowed_source_prefixes`. For an asynchronous build
failure, inspect `documents.index_status(name).error` before resubmitting.

## Embed the ASGI Application

Applications that already own an ASGI deployment can use the public factory
directly. This is an embedding API; ordinary deployments should use
`parqdb serve` instead.

```python
from parqdb.server import create_app

app = create_app(
    "/srv/parqdb",
    allowed_source_prefixes=["/srv/lakehouse"],
)
```

Do not configure multiple ASGI workers for the first server deployment.
SQLite catalog coordination, accepted index builds, and disposable caches are
process-local. A restart preserves published tables and indexes but abandons
in-progress builds.
