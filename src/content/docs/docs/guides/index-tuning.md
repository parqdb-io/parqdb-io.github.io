---
title: Tune an IVF index
description: Choose the metric, postings encoding, cluster count, and probe count using recall, latency, and I/O measurements.
---

IVF tuning separates build-time choices from query-time choices. Pick the
metric, postings encoding, and `nlist` when building the index. Tune `nprobes`
and `k` for each query workload without rebuilding.

## Start with the metric

The metric must match the embedding model and the evaluation data.

| Metric | `_distance` | Use when |
| --- | --- | --- |
| `l2_squared` | Squared Euclidean distance | The model or benchmark is defined in Euclidean space |
| `cosine` | `1 - cosine_similarity` for exact, non-zero vectors | Vector direction matters more than magnitude |

Cosine indexes normalize source and query vectors. Changing the metric requires
a rebuild; do not build with one metric and interpret results as the other.

## Choose the postings encoding

| Encoding | Candidate scoring | Trade-off |
| --- | --- | --- |
| `source` | Exact source-vector distance | Best correctness baseline; source vectors must be resolved while scoring |
| `lvq8` | Approximate 8-bit local quantization | Practical balance of recall and index I/O |
| `lvq4` | Approximate packed 4-bit local quantization | Smaller postings; validate the additional recall loss on your data |

LVQ4 and LVQ8 do not automatically rerank candidates against the source
vectors. Use `source` or `bypass_vector_index()` when producing an exact
reference result.

## Set `nlist`

`nlist` is the number of leaf clusters. More clusters make each posting list
smaller, but add centroid metadata and make routing and publication more
granular. It must be positive and cannot exceed the indexed row count.

There is no universal value based only on row count. Embedding dimension,
distribution, filters, storage latency, and expected `k` all change the best
choice. Build a small number of candidates with representative data rather
than treating a benchmark's `nlist` as a default.

```python
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
```

Changing `nlist`, the metric, or the encoding requires building or refreshing
the index.

## Sweep `nprobes`

`nprobes` selects how many clusters a query reads and must be between `1` and
`nlist`. Increasing it generally raises recall and also increases candidate
work and storage I/O. At `nprobes = nlist`, every indexed row is considered,
although LVQ distances remain approximate.

```python
base = (
    documents.search(query_vector, column="embedding")
    .limit(10)
    .select(["document_id"])
)

exact = session.collect(base.bypass_vector_index())
for probes in (8, 16, 32, 64):
    approximate = session.collect(base.nprobes(probes))
    # Compare keys with `exact`, and record latency and query-plan metrics.
```

Evaluate multiple real query vectors, including filtered queries and queries
with the largest expected `k`. Report at least Recall@k, p50/p95 latency,
candidate rows, and bytes read. Warm and cold cache measurements answer
different questions, so record them separately.

## Read the plan

Use `session.explain(query)` to verify that the vector index is selected. Use
`session.analyze(query)` to inspect actual operator metrics. A high recall
configuration that reads most of the index may still be the wrong operational
choice.

The published [SIFT1B result](https://github.com/parqdb-io/parqdb/tree/main/benchmarks/results/linux-x86_64-2026-08-17)
is an example of a complete, reproducible report: it records data shape,
training sample, index settings, query resources, cache state, recall, latency,
and measured reads. Treat its numbers as evidence for that workload, not as
defaults for yours.

## Keep writer tuning separate

`WriteOptions` changes Parquet file sizing, row groups, compression, and build
parallelism. These settings affect build cost and physical I/O, but they do not
change the logical meaning of `nlist` or `nprobes`. Tune them after establishing
a recall target, then repeat the I/O and latency measurements.
