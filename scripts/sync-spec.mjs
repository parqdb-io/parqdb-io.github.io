import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const websiteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const parqdbRoot = path.resolve(process.argv[2] ?? path.join(websiteRoot, "..", "parqdb"));
const sourceRoot = path.join(parqdbRoot, "spec");
const targetRoot = path.join(websiteRoot, "src", "content", "docs", "docs", "spec");

const documents = new Map([
  ["README.md", "index.md"],
  ["catalog.md", "catalog.md"],
  ["metadata.md", "metadata.md"],
  ["publication-manifest.md", "publication-manifest.md"],
  ["ivf/index-schema.md", "ivf/index-schema.md"],
  ["ivf/query.md", "ivf/query.md"],
  ["storage/parquet.md", "storage/parquet.md"],
  ["storage/iceberg.md", "storage/iceberg.md"],
]);

function frontmatter(document, target) {
  const match = document.match(/^---\n[\s\S]*?\n---\n+/);
  if (!match) throw new Error(`missing frontmatter: ${target}`);
  return match[0];
}

function routeFor(source) {
  if (source === "README.md") return "/docs/spec";
  return `/docs/spec/${source.replace(/\.md$/, "")}`;
}

function rewriteLinks(document, source) {
  const sourceDirectory = path.posix.dirname(source);
  const markdownLinks = document.replace(
    /\]\(([^):]+\.md)(#[^)]+)?\)/g,
    (_match, relative, anchor = "") => {
      const resolved = path.posix.normalize(path.posix.join(sourceDirectory, relative));
      return `](${routeFor(resolved)}${anchor})`;
    },
  );
  return markdownLinks.replace(
    "](fixtures/v1/)",
    "](https://github.com/parqdb-io/parqdb/tree/main/spec/fixtures/v1)",
  );
}

for (const [source, target] of documents) {
  const sourcePath = path.join(sourceRoot, source);
  const targetPath = path.join(targetRoot, target);
  const [sourceDocument, targetDocument] = await Promise.all([
    readFile(sourcePath, "utf8"),
    readFile(targetPath, "utf8"),
  ]);
  const body = sourceDocument.replace(/^# [^\n]+\n+/, "");
  await writeFile(
    targetPath,
    `${frontmatter(targetDocument, target)}${rewriteLinks(body, source)}`,
  );
}

console.log(`synchronized ${documents.size} specification pages from ${sourceRoot}`);
