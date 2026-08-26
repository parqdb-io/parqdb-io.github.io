---
title: Publish for the browser
description: Build and publish an immutable IVF-LVQ index for direct HTTP Range queries in WebAssembly.
banner:
  content: 'You are viewing the ParqDB 0.3 documentation snapshot. <a href="/docs">Read the latest documentation →</a>'
---

ParqDB can publish a source table, vector index, and optional embedding model as immutable objects behind one top-level `manifest.json`. A compatible browser reads only the necessary Parquet byte ranges and ranks candidates in WebAssembly.

:::note
Browser publication currently supports public HTTPS object storage, IVF-LVQ4 and IVF-LVQ8, and immutable manifests. Private credentials and refresh are outside the current browser format.
:::

## Install the publisher

```bash
python -m pip install "parqdb[publish]"
```

The extra includes the pinned MiniLM ONNX embedding workflow and S3 publication dependencies. It is not required for ordinary embedded vector search.

## Publish existing vectors

Your source key must be a dense, ordered, non-null `int64` column starting at zero.

```bash
parqdb publish \
  --source documents.parquet \
  --key chunk_id \
  --vector-column embedding \
  --nlist 4096 \
  --encoding lvq8 \
  --destination s3://my-bucket/kb/v1 \
  --s3-endpoint https://ACCOUNT_ID.r2.cloudflarestorage.com \
  --s3-region auto \
  --public-url https://data.example.com/kb/v1
```

Credentials come from `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. The publisher refuses to overwrite an existing prefix.

## Build embeddings from text

Use one or more `--text-column` options instead of `--vector-column`:

```bash
parqdb publish \
  --source documents.parquet \
  --key chunk_id \
  --text-column title \
  --text-column section \
  --text-column text \
  --nlist 4096 \
  --destination s3://my-bucket/kb/v1 \
  --public-url https://data.example.com/kb/v1 \
  --include-source \
  --include-model
```

The pinned MiniLM model is used for both offline source embeddings and browser query embeddings. This parity is required: vectors produced by a different model are not comparable.

## Choose what to publish

- The vector index is always included.
- `--include-source` publishes the source Parquet file for payload lookup.
- `--include-model` publishes the pinned text embedding model and requires `--text-column`.
- Without source data, browser results contain source keys and `_distance` only.

## HTTP requirements

The public endpoint must:

1. serve every object over HTTPS;
2. support byte ranges and return `206 Partial Content` with a valid `Content-Range`;
3. allow the browser origin through CORS; and
4. preserve immutable object URLs.

Unless `--no-verify-http` is passed, publication verifies public HTTP Range and CORS behavior before it succeeds. The top-level manifest is exposed only after all referenced objects have been uploaded.

## Build a complete knowledge base

[`parqdb-knowledgebase`](https://github.com/parqdb-io/parqdb-knowledgebase) adds token-aware document chunking, source metadata, and a deployable search UI on top of the browser publication format.

Try the published Wikipedia index at [search.parqdb.io](https://search.parqdb.io/).
