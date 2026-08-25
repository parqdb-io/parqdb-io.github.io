import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";
import sitemap from "@astrojs/sitemap";

const site = process.env.SITE_URL ?? "https://parqdb.io";
const base = process.env.BASE_PATH ?? "/";

export default defineConfig({
  site,
  base,
  trailingSlash: "never",
  integrations: [
    starlight({
      title: "ParqDB",
      description:
        "Billion-scale embedded vector search built on Parquet and Arrow.",
      logo: {
        light: "./src/assets/logo.svg",
        dark: "./src/assets/logo-dark.svg",
        replacesTitle: true,
      },
      favicon: "/favicon.svg",
      customCss: ["./src/styles/starlight.css"],
      components: {
        Head: "./src/components/docs/Head.astro",
      },
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/parqdb-io/parqdb",
        },
      ],
      editLink: {
        baseUrl: "https://github.com/parqdb-io/parqdb-io.github.io/edit/main/",
      },
      head: [
        {
          tag: "meta",
          attrs: { name: "theme-color", content: "#07152f" },
        },
        {
          tag: "meta",
          attrs: {
            property: "og:image",
            content: new URL("/og.svg", site).toString(),
          },
        },
      ],
      sidebar: [
        {
          label: "Start",
          items: [
            { label: "Documentation", slug: "docs" },
            { label: "Getting started", slug: "docs/getting-started" },
            { label: "Core concepts", slug: "docs/concepts" },
          ],
        },
        {
          label: "Guides",
          items: [
            { label: "Embedded ParqDB", slug: "docs/guides/embedded" },
            { label: "Publish for the browser", slug: "docs/guides/browser" },
            { label: "Run a server", slug: "docs/guides/server" },
          ],
        },
        {
          label: "Reference",
          items: [
            { label: "Python API", slug: "docs/reference/python" },
            { label: "CLI", slug: "docs/reference/cli" },
            { label: "Configuration", slug: "docs/reference/configuration" },
            { label: "Troubleshooting", slug: "docs/reference/troubleshooting" },
            { label: "Current limitations", slug: "docs/reference/limitations" },
          ],
        },
        {
          label: "Project",
          items: [
            { label: "Architecture", slug: "docs/project/architecture" },
            { label: "Roadmap", slug: "docs/project/roadmap" },
            {
              label: "Open index specification ↗",
              link: "https://github.com/parqdb-io/parqdb/tree/main/spec",
              attrs: { target: "_blank", rel: "noreferrer" },
            },
            {
              label: "RFCs ↗",
              link: "https://github.com/parqdb-io/parqdb/tree/main/docs/rfcs",
              attrs: { target: "_blank", rel: "noreferrer" },
            },
          ],
        },
      ],
    }),
    sitemap(),
  ],
});
