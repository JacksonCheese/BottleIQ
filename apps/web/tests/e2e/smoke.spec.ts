import { test, expect } from "@playwright/test";
test.use({ reducedMotion: "reduce" });
test("demo owner can inspect inventory and edit/export a Smart Order", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Stop guessing what to order." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Try the Demo" }).click();
  await expect(
    page.getByRole("heading", { name: "Good morning, Alex." }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Build this week’s order/i }),
  ).toHaveAttribute("href", "/smart-orders");
  await expect(
    page.getByRole("link", { name: /Prevent stockouts/i }),
  ).toHaveAttribute("href", "/inventory?status=stockout");
  await expect(
    page.getByRole("link", { name: /Free trapped cash/i }),
  ).toHaveAttribute("href", "/inventory?status=slow");
  await expect(
    page.getByRole("heading", { name: "Order first" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Pause buying" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Inventory summary" }),
  ).toContainText("Total inventory value");
  await page.screenshot({
    path: "../../docs/screenshots/dashboard.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Products", exact: true }).click();
  await page.getByLabel("Search inventory").fill("BTL-0001");
  await expect(
    page.getByRole("link", { name: "Cedar Ridge Reserve Whiskey" }),
  ).toBeVisible();
  const [productResponse] = await Promise.all([
    page.waitForResponse((response) =>
      /\/api\/products\/[^?]+\?store_id=/.test(response.url()),
    ),
    page.getByRole("link", { name: "Cedar Ridge Reserve Whiskey" }).click(),
  ]);
  const product = await productResponse.json();
  expect(product.recommended_cases).toBeGreaterThan(2);
  expect(product.inventory_position).toBe(
    product.current_quantity + product.incoming_units,
  );
  expect(product.recommended_cases).toBe(
    Math.ceil(
      Math.max(0, product.target_stock - product.inventory_position) /
        product.units_per_case,
    ),
  );
  await expect(
    page.getByText(
      `Recommended: ${product.recommended_cases} cases · ${product.recommended_units} units`,
    ),
  ).toBeVisible();
  const incomingUnits = product.units_per_case * 2;
  await page.getByLabel("Confirmed incoming units").fill(String(incomingUnits));
  await page
    .getByLabel("Expected date")
    .fill(new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10));
  await page.getByLabel("Order reference (optional)").fill("Pilot smoke test");
  const [updatedResponse] = await Promise.all([
    page.waitForResponse((response) =>
      /\/api\/products\/[^?]+\?store_id=/.test(response.url()),
    ),
    page.getByRole("button", { name: "Add incoming stock" }).click(),
  ]);
  const updated = await updatedResponse.json();
  expect(updated.incoming_units).toBe(product.incoming_units + incomingUnits);
  expect(updated.inventory_position).toBe(
    updated.current_quantity + updated.incoming_units,
  );
  expect(updated.recommended_cases).toBe(
    Math.ceil(
      Math.max(0, updated.target_stock - updated.inventory_position) /
        updated.units_per_case,
    ),
  );
  expect(updated.recommended_cases).toBeLessThan(product.recommended_cases);
  expect(updated.recommended_units).toBe(
    updated.recommended_cases * updated.units_per_case,
  );
  await expect(
    page.getByText(
      `Recommended: ${updated.recommended_cases} cases · ${updated.recommended_units} units`,
    ),
  ).toBeVisible();
  await page.getByLabel("Units arrived").fill(String(product.units_per_case));
  const [receivedResponse] = await Promise.all([
    page.waitForResponse((response) =>
      /\/api\/products\/[^?]+\?store_id=/.test(response.url()),
    ),
    page.getByRole("button", { name: "Record receipt" }).click(),
  ]);
  const received = await receivedResponse.json();
  expect(received.current_quantity).toBe(
    updated.current_quantity + product.units_per_case,
  );
  expect(received.incoming_units).toBe(
    updated.incoming_units - product.units_per_case,
  );
  expect(received.inventory_position).toBe(updated.inventory_position);
  expect(received.recommended_cases).toBe(updated.recommended_cases);
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
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../../docs/screenshots/smart-order.png",
    fullPage: true,
  });
});
test("responsive dashboard and navigation stay usable", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.getByRole("button", { name: "Try the Demo" }).click();
  await expect(
    page.getByRole("heading", { name: "Good morning, Alex." }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Build this week’s order/i }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../docs/screenshots/mobile-dashboard.png",
    fullPage: true,
  });
  await expect(page.getByRole("link", { name: "Today" })).toBeHidden();
  for (const width of [768, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(
      page.getByRole("link", { name: /Build this week’s order/i }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Update data", exact: true }).click();
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
  const email = `qa-${Date.now()}@example.com`;
  const password = "synthetic-browser-password-123";
  await page.goto("/signup");
  await page.getByLabel("Your name").fill("Pilot Tester");
  await page.getByLabel("Business name").fill("Synthetic Onboarding Shop");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page.getByLabel("Store name").fill("Test Downtown");
  await page.getByRole("button", { name: "Create store", exact: true }).click();
  await page
    .getByRole("link", { name: "Import your data", exact: true })
    .click();
  await page.getByLabel("CSV file").setInputFiles({
    name: "inventory.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Code,product_name,quantity_on_hand,unit_cost,retail_price,vendor,units_per_case\n001,Synthetic Test Whiskey,8,18,29,Test Distributor,12\n",
    ),
  });
  await page.getByLabel("Map sku", { exact: true }).selectOption("Code");
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByRole("status")).toContainText("1 imported");
  await page.getByLabel("CSV file").setInputFiles({
    name: "invalid-inventory.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "sku,product_name,quantity_on_hand,unit_cost,retail_price\n002,Bad gin,not-a-number,10,18\n",
    ),
  });
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByRole("status")).toContainText("1 rejected");
  await expect(page.getByRole("status")).toContainText("Fix the issues below");
  await expect(page.getByRole("status")).toContainText("Row 2:");
  await page.getByRole("button", { name: "Sales", exact: true }).click();
  const rows = ["date,sku,product_name,units_sold,revenue,unit_price"];
  for (let i = 90; i >= 1; i--) {
    const day = new Date();
    day.setDate(day.getDate() - i);
    rows.push(
      `${day.toISOString().slice(0, 10)},001,Synthetic Test Whiskey,4,116,29`,
    );
  }
  await page.getByLabel("CSV file").setInputFiles({
    name: "sales.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(rows.join("\n")),
  });
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByRole("status")).toContainText("90 imported");
  await page.getByRole("button", { name: "Purchases", exact: true }).click();
  await page.getByLabel("CSV file").setInputFiles({
    name: "purchases.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      `purchase_date,vendor,sku,quantity,unit_cost,invoice_number\n${new Date(Date.now() - 86400000).toISOString().slice(0, 10)},Test Distributor,001,12,18,PILOT-001\n`,
    ),
  });
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByRole("status")).toContainText("1 imported");
  await page.getByRole("link", { name: "Products", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Synthetic Test Whiskey" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Today", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Good morning, Pilot." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Order", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Create draft" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Pilot Tester/ }).click();
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Good morning, Pilot." }),
  ).toBeVisible();
});
