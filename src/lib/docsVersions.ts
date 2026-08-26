export const docsVersions = [
  { id: "latest", label: "latest" },
  { id: "0.3", label: "0.3" },
  { id: "0.2", label: "0.2" },
] as const;

export type DocsVersion = (typeof docsVersions)[number]["id"];

const docsRoot = "/docs";
const versionPattern = /^\/docs\/(0\.3|0\.2)(?=\/|$)/;

export function currentDocsVersion(pathname: string): DocsVersion {
  const match = normalizePath(pathname).match(versionPattern);
  return match ? (match[1] as DocsVersion) : "latest";
}

export function docsPathForVersion(pathname: string, version: DocsVersion): string {
  const normalized = normalizePath(pathname);
  const suffix = normalized.replace(versionPattern, docsRoot).slice(docsRoot.length);
  return version === "latest" ? `${docsRoot}${suffix}` : `${docsRoot}/${version}${suffix}`;
}

export function versionedDocsHref(href: string, version: DocsVersion): string {
  if (!href.startsWith(docsRoot)) return href;
  return docsPathForVersion(href, version);
}

export function normalizePath(pathname: string): string {
  return pathname.length > 1 ? pathname.replace(/\/$/, "") : pathname;
}
