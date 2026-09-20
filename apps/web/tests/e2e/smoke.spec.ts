import { test, expect } from "@playwright/test";
test("demo owner can inspect inventory and edit/export a Smart Order", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Stop guessing what to order." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Try the Demo" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view, Alex." }),
  ).toBeVisible();
  await expect(page.getByText("Total inventory value")).toBeVisible();
  await page.screenshot({
    path: "../../docs/screenshots/dashboard.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Inventory", exact: true }).click();
  await page.getByLabel("Search inventory").fill("BTL-0001");
  await expect(
    page.getByRole("link", { name: "Cedar Ridge Reserve Whiskey" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Cedar Ridge Reserve Whiskey" }).click();
  await expect(page.getByText("Recommended: 8 cases · 96 units")).toBeVisible();
  await page
    .getByRole("link", { name: "Review Smart Order", exact: true })
    .click();
  await page.getByRole("button", { name: "Create draft" }).first().click();
  const cases = page.getByRole("spinbutton").first();
  await expect(cases).toBeVisible();
  await cases.fill("1");
  await expect(page.getByRole("link", { name: "Export CSV" })).toHaveAttribute(
    "aria-disabled",
    "true",
  );
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Changes saved.")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toContain("bottleiq-order-");
  await page.screenshot({
    path: "../../docs/screenshots/smart-order.png",
    fullPage: true,
  });
});
test("responsive navigation stays usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Try the Demo" }).click();
  await expect(
    page.getByRole("heading", { name: "A clearer view, Alex." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Import data", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Bring your store into focus." }),
  ).toBeVisible();
  await page.screenshot({
    path: "../../docs/screenshots/mobile-import.png",
    fullPage: true,
  });
});

test("new owner can sign up, create a store, map CSV columns, and import data", async ({
  page,
}) => {
  await page.goto("/signup");
  await page.getByLabel("Your name").fill("Pilot Tester");
  await page.getByLabel("Business name").fill("Synthetic Onboarding Shop");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`qa-${Date.now()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-browser-password-123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page.getByLabel("Store name").fill("Test Downtown");
  await page.getByRole("button", { name: "Create store", exact: true }).click();
  await page
    .getByRole("link", { name: "Import your data", exact: true })
    .click();
  await page
    .getByLabel("CSV file")
    .setInputFiles({
      name: "inventory.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(
        "Code,product_name,quantity_on_hand,unit_cost,retail_price,vendor,units_per_case\n001,Synthetic Test Whiskey,8,18,29,Test Distributor,12\n",
      ),
    });
  await page.getByLabel("Map sku", { exact: true }).selectOption("Code");
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByRole("status")).toContainText("1 imported");
  await page.getByRole("button", { name: "Sales", exact: true }).click();
  const rows = ["date,sku,product_name,units_sold,revenue,unit_price"];
  for (let i = 90; i >= 1; i--) {
    const day = new Date();
    day.setDate(day.getDate() - i);
    rows.push(
      `${day.toISOString().slice(0, 10)},001,Synthetic Test Whiskey,4,116,29`,
    );
  }
  await page
    .getByLabel("CSV file")
    .setInputFiles({
      name: "sales.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(rows.join("\n")),
    });
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByRole("status")).toContainText("90 imported");
  await page.getByRole("link", { name: "Inventory", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Synthetic Test Whiskey" }),
  ).toBeVisible();
  await expect(page.getByText("8 cases")).toBeVisible();
});
