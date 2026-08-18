# ParqDB Demo

This repository deploys the official [ParqDB](https://github.com/parqdb-io/parqdb)
browser demo to [parqdb-io.github.io](https://parqdb-io.github.io/).

The site embeds search text with a pinned quantized MiniLM ONNX model, discovers
an immutable 100,000-document English Wikipedia index from `manifest.json`,
reads selected Parquet byte ranges over HTTP, runs LVQ distance and top-k in
WebAssembly, and looks up article rows by a stable integer `doc_id`. No query
API or vector database server is involved.

## Deployment

The demo page is maintained in [`index.html`](./index.html). The reproducible
data pipeline is [`scripts/build_wiki_demo.py`](./scripts/build_wiki_demo.py).
It pins both the Wikimedia dataset and model revisions. The Pages workflow
combines the committed immutable data objects with a pinned ParqDB revision,
the browser client, WebAssembly kernels, and local ONNX Runtime assets.

The ParqDB revision is intentionally immutable so the deployed client, package
format, and WebAssembly kernel cannot drift independently.
