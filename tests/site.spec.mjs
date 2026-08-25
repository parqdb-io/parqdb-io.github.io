import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("homepage presents the product and primary paths", async ({ page }, testInfo) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Billion-scale vector search, built on Parquet.",
    }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /Get started/ }).first()).toBeVisible();
  await expect(page.getByText("63.05 ms")).toBeVisible();
  await expect(page.getByText("Object storage becomes the query endpoint.")).toBeVisible();

  const bodyWidth = await page.locator("body").evaluate((element) => element.scrollWidth);
  const viewportWidth = page.viewportSize()?.width ?? bodyWidth;
  expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);

  await page.screenshot({
    path: testInfo.outputPath("homepage.png"),
    fullPage: true,
  });
});

test("documentation navigation and search load", async ({ page }, testInfo) => {
  await page.goto("/docs/getting-started");

  await expect(page.getByRole("heading", { level: 1, name: "Getting started" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Search/ })).toBeVisible();
  if (testInfo.project.name === "mobile") {
    await page.locator('button[aria-controls="starlight__sidebar"]').click();
  }
  await expect(page.getByRole("link", { name: "Python API" }).first()).toBeVisible();

  await page.screenshot({
    path: testInfo.outputPath("docs-getting-started.png"),
    fullPage: true,
  });
});

test("key pages have no automated accessibility violations", async ({ page }) => {
  for (const path of ["/", "/docs", "/docs/getting-started"]) {
    await page.goto(path);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations, `${path}: ${JSON.stringify(results.violations, null, 2)}`).toEqual([]);
  }
});

test("all internal pages and links resolve", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "One crawl is sufficient");
  const pending = ["/"];
  const visited = new Set();

  while (pending.length > 0) {
    const path = pending.shift();
    if (!path || visited.has(path)) continue;
    visited.add(path);

    const response = await page.goto(path);
    expect(response?.ok(), `${path} returned ${response?.status()}`).toBe(true);

    const links = await page.locator("a[href]").evaluateAll((anchors) =>
      anchors.map((anchor) => anchor.href),
    );
    for (const href of links) {
      const url = new URL(href);
      if (url.origin !== "http://127.0.0.1:4321") continue;
      const next = `${url.pathname}${url.search}`;
      if (!visited.has(next) && !pending.includes(next)) pending.push(next);
    }
  }

  expect(visited.size).toBeGreaterThanOrEqual(14);
});
