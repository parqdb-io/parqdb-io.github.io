# ParqDB website

Official website and documentation for [ParqDB](https://github.com/parqdb-io/parqdb).

- Production URL: `https://parqdb.io`
- Browser demo: `https://search.parqdb.io`
- Framework: [Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/)

## Develop

Node.js 22.19 or newer is required.

```bash
npm install
npm run dev
```

Run the production checks before submitting a change:

```bash
npm run build
```

## Content ownership

This repository is the canonical source for ParqDB's public documentation. Product specifications, benchmark evidence, and implementation RFCs remain with the main [`parqdb`](https://github.com/parqdb-io/parqdb) repository and are linked from the site.

Documentation lives in `src/content/docs/`. The marketing homepage lives in `src/pages/index.astro`.

## Documentation versions

`/docs` is the permanent URL for documentation built from the current main
branch and appears as `latest` in the version selector. Frozen minor-version
snapshots live below `/docs/<minor>`, starting with `/docs/0.2` for the
`v0.2.0rc3` release line. Historical snapshots are excluded from site search
so results always prefer the current API.

## Deployment

The Pages workflow publishes every push to `main` at the root of
`https://parqdb.io`. The repository is also the canonical GitHub organization
site at `https://parqdb-io.github.io`.
