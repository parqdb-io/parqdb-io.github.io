#!/usr/bin/env python3
"""Build the deterministic 100k-document ParqDB Wikipedia browser demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import urllib.request
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import duckdb
import numpy as np
import onnxruntime as ort
import parqdb
import pyarrow as pa
import pyarrow.parquet as pq
from transformers import AutoTokenizer

WIKIPEDIA_REVISION = "b04c8d1ceb2f5cd4588862100d08de323dccfbaa"
WIKIPEDIA_SHARD = "20231101.en/train-00000-of-00041.parquet"
WIKIPEDIA_URL = (
    "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/"
    f"{WIKIPEDIA_REVISION}/{WIKIPEDIA_SHARD}"
)
MODEL_REPOSITORY = "Xenova/all-MiniLM-L6-v2"
MODEL_REVISION = "751bff37182d3f1213fa05d7196b954e230abad9"
MODEL_FILES = (
    "config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
    "onnx/model_quantized.onnx",
)
MODEL_DIMENSION = 384
MODEL_MAX_LENGTH = 256
MODEL_PARITY_TEXT = "ParqDB reads immutable Parquet indexes with HTTP Range requests."
DEFAULT_ROWS = 100_000
DEFAULT_NLIST = 4_096
SOURCE_ROW_GROUP_ROWS = 128
_PARAGRAPH = re.compile(r"\n\s*\n+")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, default=Path(".demo-build"))
    parser.add_argument("--output", type=Path, default=Path("public/wiki"))
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--nlist", type=int, default=DEFAULT_NLIST)
    parser.add_argument("--threads", type=int, default=16)
    parser.add_argument("--embedding-batch-size", type=int, default=128)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    validate_options(args)
    work = args.work.resolve()
    output = args.output.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.force:
        raise SystemExit(f"output already exists: {output}; pass --force to replace it")

    documents = work / "documents.parquet"
    model_root = work / "model"
    index_source = work / "index-source.parquet"
    warehouse_root = work / "parqdb"

    if not documents.exists():
        build_documents(documents, args.rows, args.threads)
    require_rows(documents, args.rows)
    download_model(model_root)
    model_metadata = model_manifest(model_root, args.threads)
    if not index_source.exists():
        embed_documents(
            documents,
            index_source,
            model_root,
            args.embedding_batch_size,
            args.threads,
        )
    require_rows(index_source, args.rows)
    package_root = build_index(
        index_source,
        warehouse_root,
        args.nlist,
        args.threads,
    )

    staged = work / "publish"
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir()
    copy_package(package_root, staged / "index")
    shutil.copy2(documents, staged / "documents.parquet")
    shutil.copytree(model_root, staged / "models" / "all-MiniLM-L6-v2")
    write_json(
        staged / "source-manifest.json",
        {
            "format-version": 1,
            "rows": args.rows,
            "row-group-rows": SOURCE_ROW_GROUP_ROWS,
            "object": object_descriptor(
                staged / "documents.parquet", "documents.parquet"
            ),
            "key": {"name": "doc_id", "type": "long"},
            "columns": ["doc_id", "page_id", "title", "text", "url"],
            "dataset": {
                "repository": "wikimedia/wikipedia",
                "revision": WIKIPEDIA_REVISION,
                "configuration": "20231101.en",
                "shard": WIKIPEDIA_SHARD,
                "selection": f"first {args.rows} qualifying rows in pinned shard order",
            },
            "embedding": model_metadata,
        },
    )
    write_json(staged / "model.json", model_metadata)

    if output.exists():
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staged.replace(output)
    print(json.dumps(summary(output), indent=2, sort_keys=True))


def validate_options(args: argparse.Namespace) -> None:
    if args.rows <= 0:
        raise SystemExit("--rows must be positive")
    if args.nlist <= 0 or args.nlist > args.rows:
        raise SystemExit("--nlist must be in [1, rows]")
    if not 1 <= args.threads <= 16:
        raise SystemExit("--threads must be in [1, 16]")
    if args.embedding_batch_size <= 0:
        raise SystemExit("--embedding-batch-size must be positive")


def build_documents(path: Path, rows: int, threads: int) -> None:
    raw_limit = max(rows * 2, rows + 10_000)
    connection = duckdb.connect()
    connection.execute(f"SET threads = {threads}")
    reader = connection.execute(
        "SELECT id, title, url, text FROM read_parquet(?) LIMIT ?",
        [WIKIPEDIA_URL, raw_limit],
    ).to_arrow_reader(batch_size=4_096)
    doc_ids: list[int] = []
    page_ids: list[int] = []
    titles: list[str] = []
    texts: list[str] = []
    urls: list[str] = []
    for batch in reader:
        for source in batch.to_pylist():
            lead = lead_paragraph(source["text"])
            title = normalize_text(source["title"])
            if len(lead) < 80 or not title:
                continue
            doc_ids.append(len(doc_ids))
            page_ids.append(int(source["id"]))
            titles.append(title)
            texts.append(lead)
            urls.append(str(source["url"]))
            if len(doc_ids) == rows:
                break
        if len(doc_ids) == rows:
            break
    connection.close()
    if len(doc_ids) != rows:
        raise RuntimeError(
            f"pinned Wikipedia shard yielded only {len(doc_ids)} qualifying rows"
        )
    table = pa.Table.from_arrays(
        [
            pa.array(doc_ids, type=pa.int64()),
            pa.array(page_ids, type=pa.int64()),
            pa.array(titles, type=pa.string()),
            pa.array(texts, type=pa.string()),
            pa.array(urls, type=pa.string()),
        ],
        schema=pa.schema(
            [
                pa.field("doc_id", pa.int64(), nullable=False),
                pa.field("page_id", pa.int64(), nullable=False),
                pa.field("title", pa.string(), nullable=False),
                pa.field("text", pa.string(), nullable=False),
                pa.field("url", pa.string(), nullable=False),
            ]
        ),
    )
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=6,
        row_group_size=SOURCE_ROW_GROUP_ROWS,
        data_page_size=16 * 1024,
        write_batch_size=SOURCE_ROW_GROUP_ROWS,
        write_page_index=True,
    )


def lead_paragraph(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    for paragraph in _PARAGRAPH.split(text):
        normalized = normalize_text(paragraph)
        if len(normalized) >= 80:
            return normalized[:1_600]
    return normalize_text(text)[:1_600]


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split())


def download_model(root: Path) -> None:
    for relative in MODEL_FILES:
        destination = root / relative
        if destination.exists() and destination.stat().st_size > 0:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = (
            f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/"
            f"{MODEL_REVISION}/{relative}"
        )
        temporary = destination.with_suffix(destination.suffix + ".part")
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(destination)


def model_manifest(root: Path, threads: int) -> dict[str, object]:
    tokenizer = AutoTokenizer.from_pretrained(root, local_files_only=True)
    session = onnx_session(root, threads)
    probe = encode_texts(session, tokenizer, [MODEL_PARITY_TEXT])[0]
    return {
        "repository": MODEL_REPOSITORY,
        "revision": MODEL_REVISION,
        "runtime": "onnx",
        "onnx-file": "onnx/model_quantized.onnx",
        "onnx-sha256": sha256(root / "onnx/model_quantized.onnx"),
        "dimension": MODEL_DIMENSION,
        "max-length": MODEL_MAX_LENGTH,
        "pooling": "attention-mask-mean",
        "normalize": True,
        "input-template": "{title}\\n\\n{text}",
        "parity-probe": {
            "text": MODEL_PARITY_TEXT,
            "vector": [round(float(value), 8) for value in probe],
            "max-absolute-error": 0.002,
        },
    }


def embed_documents(
    documents: Path,
    output: Path,
    model_root: Path,
    batch_size: int,
    threads: int,
) -> None:
    tokenizer = AutoTokenizer.from_pretrained(model_root, local_files_only=True)
    session = onnx_session(model_root, threads)
    schema = pa.schema(
        [
            pa.field("doc_id", pa.int64(), nullable=False),
            pa.field(
                "embedding",
                pa.list_(
                    pa.field("element", pa.float32(), nullable=False), MODEL_DIMENSION
                ),
                nullable=False,
            ),
        ]
    )
    writer = pq.ParquetWriter(output, schema, compression="zstd", compression_level=3)
    written = 0
    try:
        parquet = pq.ParquetFile(documents)
        for source in parquet.iter_batches(
            batch_size=batch_size,
            columns=["doc_id", "title", "text"],
        ):
            rows = source.to_pylist()
            texts = [f"{row['title']}\n\n{row['text']}" for row in rows]
            vectors = encode_texts(session, tokenizer, texts)
            if vectors.shape[1] != MODEL_DIMENSION or not np.isfinite(vectors).all():
                raise RuntimeError("embedding model returned an invalid matrix")
            flat = pa.array(vectors.reshape(-1), type=pa.float32())
            embeddings = pa.FixedSizeListArray.from_arrays(
                flat,
                type=schema.field("embedding").type,
            )
            batch = pa.RecordBatch.from_arrays(
                [source.column("doc_id"), embeddings],
                schema=schema,
            )
            writer.write_batch(batch, row_group_size=8_192)
            written += batch.num_rows
            if written % 10_000 == 0:
                print(f"embedded {written:,} documents", flush=True)
    finally:
        writer.close()


def onnx_session(model_root: Path, threads: int) -> ort.InferenceSession:
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    return ort.InferenceSession(
        model_root / "onnx/model_quantized.onnx",
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )


def encode_texts(
    session: ort.InferenceSession,
    tokenizer: Any,
    texts: list[str],
) -> np.ndarray:
    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=MODEL_MAX_LENGTH,
        return_tensors="np",
    )
    input_names = {item.name for item in session.get_inputs()}
    feeds = {
        name: np.asarray(encoded[name], dtype=np.int64)
        for name in input_names
        if name in encoded
    }
    hidden = np.asarray(session.run(None, feeds)[0], dtype=np.float32)
    mask = np.asarray(encoded["attention_mask"], dtype=np.float32)[..., None]
    vectors = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1.0)
    vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    return vectors


def build_index(source: Path, root: Path, nlist: int, threads: int) -> Path:
    existing = find_package(root)
    if existing is not None:
        validate_package(existing, source, nlist)
        return existing
    config = (
        parqdb.SessionConfig()
        .with_target_partitions(threads)
        .set("parqdb.build.dop", str(threads))
    )
    session = parqdb.connect(root, config=config)
    try:
        session.register_parquet("wiki", source)
        table = session.table("wiki")
        table.create_index(
            "wiki_embedding",
            column="embedding",
            key=["doc_id"],
            config=parqdb.IVF(nlist=nlist, encoding="lvq8", metric="cosine"),
            writer_options=parqdb.WriteOptions(
                partitions=threads,
                compression="zstd(3)",
                target_file_size=64 * 1024 * 1024,
                write_batch_rows=8_192,
            ),
            wait_timeout=timedelta(hours=3),
        )
        table.wait_for_index("wiki_embedding", timeout=timedelta(hours=3))
        warehouse = Path(unquote(urlparse(session.warehouse).path))
    finally:
        session.close()
    package = find_package(warehouse)
    if package is None:
        raise RuntimeError("ParqDB build completed without a static manifest.json")
    return package


def validate_package(package: Path, source: Path, nlist: int) -> None:
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    index = manifest.get("index", {})
    expected = {
        "metric": "cosine",
        "posting-encoding": "lvq8",
        "dimension": MODEL_DIMENSION,
        "nlist": nlist,
        "ntotal": pq.ParquetFile(source).metadata.num_rows,
        "source-key-fields": [{"name": "doc_id", "type": "long"}],
    }
    if index != expected:
        raise RuntimeError(
            "cached ParqDB package does not match this build; use a fresh --work path"
        )


def find_package(root: Path) -> Path | None:
    if not root.exists():
        return None
    for path in sorted(root.rglob("manifest.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if value.get("format-version") == 1 and "package-uuid" in value:
            return path.parent
    return None


def copy_package(source: Path, destination: Path) -> None:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    paths = {
        "manifest.json",
        manifest["hierarchy"]["roots"]["path"],
        manifest["hierarchy"]["centroids"]["path"],
        *(entry["path"] for entry in manifest["postings"]["files"]),
    }
    native_manifest = source / "ivf_postings" / "manifest.json"
    if native_manifest.exists():
        paths.add("ivf_postings/manifest.json")
    for relative in sorted(paths):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)


def require_rows(path: Path, expected: int) -> None:
    actual = pq.ParquetFile(path).metadata.num_rows
    if actual != expected:
        raise RuntimeError(f"{path} contains {actual} rows, expected {expected}")


def object_descriptor(path: Path, relative: str) -> dict[str, object]:
    return {"path": relative, "size": path.stat().st_size, "sha256": sha256(path)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def summary(root: Path) -> dict[str, Any]:
    files = [path for path in root.rglob("*") if path.is_file()]
    return {
        "output": os.fspath(root),
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
        "manifest": os.fspath(root / "index" / "manifest.json"),
    }


if __name__ == "__main__":
    main()
