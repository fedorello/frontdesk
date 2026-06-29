import type { MetadataRoute } from "next";

import { SITE_URL } from "./lib/site";

// The public, indexable routes. Keep in sync when adding top-level marketing pages.
const ROUTES = ["", "/privacy", "/terms"] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  return ROUTES.map((path) => ({
    url: `${SITE_URL}${path}`,
    changeFrequency: "monthly",
    priority: path === "" ? 1 : 0.5,
  }));
}
