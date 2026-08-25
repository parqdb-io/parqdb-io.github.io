---
title: CLI
description: Reference for the ParqDB server, configuration, and publication commands.
---

Install the base command with ParqDB:

```bash
python -m pip install parqdb
parqdb --help
```

## `parqdb serve`

Run the experimental HTTP server:

```bash
parqdb serve
parqdb serve --config ./parqdb-server.toml
```

The server reads `./parqdb-server.toml` when it exists. See [Run a server](../guides/server) for authorization and deployment guidance.

## `parqdb config init`

Write a default server configuration:

```bash
parqdb config init
parqdb config init --path ./parqdb-server.toml
```

## `parqdb publish`

Build or reuse an immutable browser-queryable IVF-LVQ index and publish it to a local directory or S3-compatible object storage:

```bash
python -m pip install "parqdb[publish]"

parqdb publish \
  --source documents.parquet \
  --key chunk_id \
  --vector-column embedding \
  --nlist 4096 \
  --destination s3://my-bucket/kb/v1 \
  --public-url https://data.example.com/kb/v1
```

### Required options

| Option | Meaning |
| --- | --- |
| `--source PARQUET` | Source Parquet file |
| `--key COLUMN` | Dense, ordered, non-null `int64` key starting at zero |
| `--destination PATH_OR_S3_URI` | New publication prefix |

When building a new index, provide `--nlist` and exactly one embedding input:

- `--vector-column COLUMN` for existing vectors; or
- one or more `--text-column COLUMN` options for pinned MiniLM embeddings.

Use `--index-manifest PATH` to reuse an index that has already been built.

### Index options

| Option | Default | Meaning |
| --- | --- | --- |
| `--encoding` | `lvq8` | Posting encoding: `lvq4` or `lvq8` |
| `--metric` | `cosine` | `cosine` or `l2_squared` |
| `--threads` | `8` | Build threads, from 1 through 16 |
| `--embedding-batch-size` | `128` | MiniLM embedding batch size |
| `--work` | `.parqdb-publish` | Resumable local build directory |

### Publication options

| Option | Meaning |
| --- | --- |
| `--include-source` | Publish the source table for browser payload lookup |
| `--include-model` | Publish the pinned model used by `--text-column` |
| `--public-url` | Public HTTPS base URL used in the manifest |
| `--s3-endpoint` | S3-compatible endpoint |
| `--s3-region` | S3 region; use `auto` for Cloudflare R2 |
| `--cors-origin` | Origin used for CORS verification |
| `--no-verify-http` | Skip public HTTP Range and CORS verification |

The command never overwrites an existing destination prefix. See [Publish for the browser](../guides/browser) for the full workflow.
