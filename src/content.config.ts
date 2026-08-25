import { defineCollection } from "astro:content";
import { docsLoader } from "@astrojs/starlight/loaders";
import { docsSchema } from "@astrojs/starlight/schema";

export const collections = {
  docs: defineCollection({
    loader: docsLoader({
      generateId: ({ entry }) =>
        entry
          .replace(/\.(?:markdown|mdown|mkdn|mkd|mdwn|md|mdx)$/, "")
          .replace(/\/index$/, ""),
    }),
    schema: docsSchema(),
  }),
};
