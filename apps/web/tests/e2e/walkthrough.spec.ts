import { expect, test } from "@playwright/test";

test("guided demo explains the full store-to-order process without importing examples", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await page.getByRole("button", { name: "Guided walkthrough" }).click();

  const tour = page.getByRole("dialog");
  await expect(tour).toBeVisible();
  await expect(tour).toHaveAttribute("aria-labelledby", "tour-title");
  await expect(page.getByLabel("Current store")).toHaveValue(/.+/);
  await expect(tour).toContainText("Cedar & Cask");
  const storeId = await page.getByLabel("Current store").inputValue();
  const importCount = () =>
    page.evaluate(async (id) => {
      const response = await fetch(`/api/imports?store_id=${id}`);
      return (await response.json()).length as number;
    }, storeId);
  const before = await importCount();
  await page.screenshot({
    path: "../../docs/screenshots/walkthrough-start.png",
  });

  for (const title of [
    "Bring in an inventory count",
    "Match the CSV columns",
    "Add sales history",
    "Add distributor purchases",
  ]) {
    await tour.getByRole("button", { name: "Next" }).click();
    await expect(page.getByRole("dialog", { name: title })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Example preview — not imported" }),
    ).toBeDisabled();
    if (title === "Match the CSV columns")
      await page.screenshot({
        path: "../../docs/screenshots/walkthrough-import.png",
      });
  }
  await expect(page.getByLabel("Map sku", { exact: true })).toHaveValue("sku");
  expect(await importCount()).toBe(before);

  for (const title of [
    "See the order opportunity",
    "Spot stockout risk",
    "Find cash tied up on shelves",
    "Review alerts",
    "Inspect every product",
    "Understand one recommendation",
    "Check the math and assumptions",
    "Tune the order plan",
    "Build by distributor",
    "Review and adjust the draft",
    "Export only after review",
  ]) {
    await tour.getByRole("button", { name: "Next" }).click();
    await expect(page.getByRole("dialog", { name: title })).toBeVisible();
    await expect(
      tour
        .getByRole("button", { name: "Next" })
        .or(tour.getByRole("button", { name: "Finish" })),
    ).toBeEnabled();
  }
  await expect(page.getByRole("link", { name: "Export CSV" })).toBeVisible();
  await page.screenshot({
    path: "../../docs/screenshots/walkthrough-order.png",
  });
  await tour.getByRole("button", { name: "Finish" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Walkthrough" }).click();
  await expect(
    page.getByRole("dialog", { name: /Start with your store/ }),
  ).toBeVisible();
  await tour.getByRole("button", { name: "Close walkthrough" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("guided walkthrough is usable on a phone and can be dismissed", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.getByRole("button", { name: "Guided walkthrough" }).click();
  const tour = page.getByRole("dialog");
  await expect(
    tour.getByRole("heading", { name: "Start with your store" }),
  ).toBeVisible();
  await tour.getByRole("button", { name: "Next" }).click();
  await expect(
    tour.getByRole("heading", { name: "Bring in an inventory count" }),
  ).toBeVisible();
  await expect(tour.getByRole("button", { name: "Next" })).toBeEnabled();
  const bounds = await tour.boundingBox();
  expect(bounds).not.toBeNull();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(375);
  await page.screenshot({
    path: "../../docs/screenshots/walkthrough-mobile.png",
  });
  await tour.getByRole("button", { name: "Close walkthrough" }).click();
  await expect(tour).toHaveCount(0);
});
