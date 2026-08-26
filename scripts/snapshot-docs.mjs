import { cp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const version = process.argv[2];
if (!/^\d+\.\d+$/.test(version ?? "")) {
  throw new Error("usage: npm run snapshot:docs -- <major.minor>");
}

const websiteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const docsRoot = path.join(websiteRoot, "src", "content", "docs", "docs");
const targetRoot = path.join(docsRoot, version);
const versionDirectory = /^\d+\.\d+$/;

await rm(targetRoot, { recursive: true, force: true });

const sourceEntries = await readdir(docsRoot, { withFileTypes: true });
const preservedVersions = sourceEntries
  .filter((entry) => entry.isDirectory() && versionDirectory.test(entry.name))
  .map((entry) => entry.name);

for (const entry of sourceEntries) {
  if (versionDirectory.test(entry.name)) continue;
  await cp(path.join(docsRoot, entry.name), path.join(targetRoot, entry.name), {
    recursive: true,
  });
}

async function rewriteDirectory(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      await rewriteDirectory(entryPath);
      continue;
    }
    if (!/\.mdx?$/.test(entry.name)) continue;

    let document = await readFile(entryPath, "utf8");
    const frontmatterEnd = document.indexOf("\n---", 4);
    if (!document.startsWith("---\n") || frontmatterEnd < 0) {
      throw new Error(`missing frontmatter: ${entryPath}`);
    }

    const banner =
      `banner:\n  content: 'You are viewing the ParqDB ${version} documentation snapshot. ` +
      `<a href="/docs">Read the latest documentation →</a>'\n`;
    document = `${document.slice(0, frontmatterEnd + 1)}${banner}${document.slice(frontmatterEnd + 1)}`;
    document = document.replaceAll(`\"/docs`, `\"/docs/${version}`);
    document = document.replaceAll(`'/docs`, `'/docs/${version}`);
    document = document.replaceAll(`](/docs`, `](/docs/${version}`);
    document = document.replace(/(\blink:\s*)\/docs/g, `$1/docs/${version}`);
    document = document.replaceAll(`/docs/${version}/${version}`, `/docs/${version}`);
    for (const preservedVersion of preservedVersions) {
      document = document.replaceAll(
        `/docs/${version}/${preservedVersion}`,
        `/docs/${preservedVersion}`,
      );
    }
    document = document.replaceAll(
      `<a href="/docs/${version}">Read the latest documentation`,
      `<a href="/docs">Read the latest documentation`,
    );
    await writeFile(entryPath, document);
  }
}

await rewriteDirectory(targetRoot);
console.log(`created ${version} documentation snapshot at ${targetRoot}`);
